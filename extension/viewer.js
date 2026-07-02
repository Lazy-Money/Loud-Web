// Lector de PDF de LoudVox: extrae el texto con pdf.js (Mozilla) y lo muestra
// como página limpia y legible. Sobre este texto funcionan las hotkeys, el
// clic derecho y el resaltado, igual que en cualquier página web.

import * as pdfjsLib from "./vendor/pdf.min.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc = "./vendor/pdf.worker.min.mjs";

const content = document.getElementById("content");

// --- render ---------------------------------------------------------------

function setFont(delta) {
  const cur = parseFloat(
    getComputedStyle(document.documentElement).getPropertyValue("--font-size")
  );
  const next = Math.min(40, Math.max(14, cur + delta));
  document.documentElement.style.setProperty("--font-size", `${next}px`);
}

// Agrupa los items de texto de una página en líneas (por posición Y) y las
// líneas en párrafos (por salto vertical grande o fin de oración).
function pageToParagraphs(textContent) {
  const lines = [];
  let line = null;
  for (const item of textContent.items) {
    if (!item.str) continue;
    const y = item.transform[5];
    const h = item.height || 10;
    if (line && Math.abs(y - line.y) < h * 0.5) {
      line.text += item.str;
    } else {
      if (line) lines.push(line);
      line = { text: item.str, y, h };
    }
  }
  if (line) lines.push(line);

  const paragraphs = [];
  let para = "";
  for (let i = 0; i < lines.length; i++) {
    const text = lines[i].text.trim();
    if (!text) continue;
    para = para ? `${para} ${text}` : text;
    const next = lines[i + 1];
    const bigGap = next && lines[i].y - next.y > lines[i].h * 2.2;
    const endsSentence = /[.!?…:]["»')\]]?$/.test(text);
    const nextStartsUpper = next && /^[¿¡"«(A-ZÁÉÍÓÚÜÑ0-9]/.test(next.text.trim());
    if (!next || bigGap || (endsSentence && nextStartsUpper && para.length > 200)) {
      paragraphs.push(para);
      para = "";
    }
  }
  if (para) paragraphs.push(para);
  return paragraphs;
}

async function renderPdf(data, name) {
  content.innerHTML = "<p id='placeholder'>Cargando…</p>";
  document.title = `${name} — Lector LoudVox`;
  try {
    const pdf = await pdfjsLib.getDocument({ data }).promise;
    content.innerHTML = "";
    for (let n = 1; n <= pdf.numPages; n++) {
      const page = await pdf.getPage(n);
      const textContent = await page.getTextContent();
      if (pdf.numPages > 1) {
        const mark = document.createElement("h2");
        mark.className = "page-mark";
        mark.textContent = `Página ${n} de ${pdf.numPages}`;
        content.appendChild(mark);
      }
      for (const para of pageToParagraphs(textContent)) {
        const p = document.createElement("p");
        p.textContent = para;
        content.appendChild(p);
      }
    }
    if (!content.children.length) {
      content.innerHTML =
        "<p id='placeholder'>Este PDF no contiene texto extraíble " +
        "(puede ser un escaneo/imagen).</p>";
    }
  } catch (e) {
    content.innerHTML = `<p id='placeholder'>No se pudo abrir el PDF: ${e.message}</p>`;
  }
}

async function openFile(file) {
  renderPdf(new Uint8Array(await file.arrayBuffer()), file.name);
}

// --- carga por URL (?url=…) para PDFs de internet --------------------------

const params = new URLSearchParams(location.search);
const urlParam = params.get("url");
const autoread = params.get("autoread") === "1";

if (params.get("hint") === "file") {
  content.innerHTML = `
    <div id="placeholder" style="text-align:left; max-width:34em; margin:8vh auto;">
      <p><strong>Ese PDF está en tu computadora</strong> y Brave no deja que
      LoudVox lo vea sin un permiso extra.</p>
      <p>Dos opciones:</p>
      <p><strong>A) La rápida:</strong> usá el botón <strong>📂 Abrir PDF…</strong>
      de arriba y elegí el archivo. Listo.</p>
      <p><strong>B) La definitiva (una sola vez):</strong></p>
      <ol>
        <li>Abrí <code>brave://extensions</code></li>
        <li>En LoudVox tocá <strong>Detalles</strong></li>
        <li>Activá <strong>“Permitir el acceso a las URL de archivo”</strong></li>
      </ol>
      <p>Con eso, el clic derecho → “Leer” sobre cualquier PDF local va a
      abrir este lector y empezar a leer solo.</p>
    </div>`;
}

if (urlParam) {
  fetch(urlParam)
    .then((r) => r.arrayBuffer())
    .then(async (buf) => {
      await renderPdf(new Uint8Array(buf), decodeURIComponent(urlParam).split("/").pop());
      if (autoread && document.querySelector("#content p:not(#placeholder)")) {
        window.getSelection()?.removeAllRanges();
        chrome.runtime.sendMessage({ target: "background", type: "lv-start", mode: "page" });
      }
    })
    .catch(() => {
      const isFile = urlParam.startsWith("file:");
      content.innerHTML =
        `<p id='placeholder'>No se pudo abrir el PDF automáticamente.` +
        (isFile
          ? `<br><br>Para PDFs locales: activá <strong>“Permitir el acceso a las URL de archivo”</strong> ` +
            `en <code>brave://extensions</code> → LoudVox → Detalles.<br>` +
            `O simplemente usá el botón <strong>📂 Abrir PDF…</strong> de arriba.`
          : ` Probá con el botón <strong>📂 Abrir PDF…</strong> de arriba.`) +
        `</p>`;
    });
}

// --- UI ---------------------------------------------------------------------

const fileInput = document.getElementById("file-input");
document.getElementById("open-file").addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) openFile(fileInput.files[0]);
});

document.getElementById("read-all").addEventListener("click", () => {
  window.getSelection()?.removeAllRanges(); // sin selección = desde el principio
  chrome.runtime.sendMessage({ target: "background", type: "lv-start", mode: "from-here" });
});
document.getElementById("stop").addEventListener("click", () => {
  chrome.runtime.sendMessage({ target: "background", type: "lv-stop" });
});
document.getElementById("font-plus").addEventListener("click", () => setFont(2));
document.getElementById("font-minus").addEventListener("click", () => setFont(-2));

// Arrastrar y soltar
document.body.addEventListener("dragover", (e) => {
  e.preventDefault();
  document.body.classList.add("dragover");
});
document.body.addEventListener("dragleave", () =>
  document.body.classList.remove("dragover")
);
document.body.addEventListener("drop", (e) => {
  e.preventDefault();
  document.body.classList.remove("dragover");
  const file = e.dataTransfer.files?.[0];
  if (file && file.name.toLowerCase().endsWith(".pdf")) openFile(file);
});
