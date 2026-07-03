// Lógica de la UI del visor de LoudVox.
//
// Python extrae los párrafos (files.py) y sintetiza/reproduce (reader.py);
// acá solo se muestra el documento, se manejan pestañas/recientes y se
// resalta el párrafo que está sonando. La comunicación:
//   JS → Python:  window.pywebview.api.<método>()   (ver bridge.py)
//   Python → JS:  lv.onParagraph(i) / lv.onEnd()
//
// Para los tests headless (Playwright, sin pywebview) se puede inyectar
// window.__lvTestApi con la misma interfaz que el bridge.

"use strict";

const $ = (id) => document.getElementById(id);

const state = {
  strings: {},
  tabs: [], // [{path, title, paragraphs, error}]
  active: null, // path de la pestaña activa
  readingPath: null, // path del documento que está sonando
  readingIndex: -1, // párrafo resaltado
};

function api() {
  return window.__lvTestApi || (window.pywebview && window.pywebview.api);
}

// --- i18n -------------------------------------------------------------------

function applyStrings(strings) {
  state.strings = strings || {};
  for (const el of document.querySelectorAll("[data-i18n]")) {
    const key = el.dataset.i18n;
    if (state.strings[key]) el.textContent = state.strings[key];
  }
  for (const el of document.querySelectorAll("[data-i18n-title]")) {
    const key = el.dataset.i18nTitle;
    if (state.strings[key]) el.title = state.strings[key];
  }
  document.title = state.strings.vw_title || "LoudVox";
}

// --- pestañas ----------------------------------------------------------------

function findTab(path) {
  return state.tabs.find((t) => t.path === path);
}

function addOrUpdateTab(doc) {
  let tab = findTab(doc.path);
  if (tab) {
    Object.assign(tab, doc);
  } else {
    tab = { ...doc };
    state.tabs.push(tab);
  }
  state.active = tab.path;
  render();
}

function closeTab(path) {
  const idx = state.tabs.findIndex((t) => t.path === path);
  if (idx === -1) return;
  state.tabs.splice(idx, 1);
  if (state.readingPath === path) {
    const a = api();
    if (a) a.stop();
    clearReading();
  }
  if (state.active === path) {
    const next = state.tabs[idx] || state.tabs[idx - 1];
    state.active = next ? next.path : null;
  }
  render();
}

function renderTabs() {
  const bar = $("tabs");
  bar.innerHTML = "";
  bar.hidden = state.tabs.length === 0;
  for (const tab of state.tabs) {
    const el = document.createElement("div");
    el.className = "tab" + (tab.path === state.active ? " active" : "");
    el.dataset.path = tab.path;
    el.title = tab.path;

    const title = document.createElement("span");
    title.className = "title";
    title.textContent = tab.title;
    el.appendChild(title);

    const close = document.createElement("button");
    close.className = "close";
    close.textContent = "×";
    close.title = state.strings.vw_close_tab || "Cerrar pestaña";
    close.addEventListener("click", (e) => {
      e.stopPropagation();
      closeTab(tab.path);
    });
    el.appendChild(close);

    el.addEventListener("click", () => {
      state.active = tab.path;
      render();
    });
    bar.appendChild(el);
  }
}

// --- contenido -----------------------------------------------------------------

function renderDoc() {
  const doc = $("doc");
  const welcome = $("welcome");
  const tab = findTab(state.active);

  if (!tab) {
    doc.hidden = true;
    welcome.hidden = false;
    refreshRecents();
    return;
  }
  welcome.hidden = true;
  doc.hidden = false;
  doc.innerHTML = "";

  if (tab.error) {
    const p = document.createElement("p");
    p.className = "doc-error";
    p.textContent = `${state.strings.vw_error_open || "Error:"} ${tab.error}`;
    doc.appendChild(p);
    return;
  }
  if (!tab.paragraphs || !tab.paragraphs.length) {
    const p = document.createElement("p");
    p.className = "doc-empty";
    p.textContent = state.strings.vw_empty_doc || "Documento sin texto.";
    doc.appendChild(p);
    return;
  }
  tab.paragraphs.forEach((text, i) => {
    const p = document.createElement("p");
    p.dataset.i = i;
    p.textContent = text;
    doc.appendChild(p);
  });
  // si este documento es el que está sonando, restaurar el resaltado
  if (state.readingPath === tab.path && state.readingIndex >= 0) {
    applyHighlight(state.readingIndex, false);
  }
}

function render() {
  renderTabs();
  renderDoc();
}

// --- recientes -------------------------------------------------------------------

function renderRecents(items) {
  const box = $("recents");
  box.innerHTML = "";
  if (!items || !items.length) {
    const p = document.createElement("p");
    p.id = "no-recents";
    p.textContent = state.strings.vw_no_recents || "";
    box.appendChild(p);
    return;
  }
  for (const item of items) {
    const btn = document.createElement("button");
    btn.className = "recent";
    btn.dataset.path = item.path;
    const name = document.createElement("span");
    name.textContent = `📄 ${item.title}`;
    const path = document.createElement("span");
    path.className = "path";
    path.textContent = item.path;
    btn.appendChild(name);
    btn.appendChild(path);
    btn.addEventListener("click", () => openPath(item.path));
    box.appendChild(btn);
  }
}

async function refreshRecents() {
  const a = api();
  if (!a) return;
  renderRecents(await a.get_recents());
}

// --- abrir documentos ---------------------------------------------------------------

async function openPath(path) {
  const a = api();
  if (!a) return;
  const doc = await a.open_path(path);
  if (doc) addOrUpdateTab(normalizeDoc(doc));
}

async function openDialog() {
  const a = api();
  if (!a) return;
  const doc = await a.open_file_dialog();
  if (doc) addOrUpdateTab(normalizeDoc(doc));
}

// El bridge devuelve {ok, path, title, paragraphs} o {ok:false, error}.
function normalizeDoc(doc) {
  return {
    path: doc.path,
    title: doc.title,
    paragraphs: doc.ok ? doc.paragraphs : [],
    error: doc.ok ? null : doc.error,
  };
}

// --- lectura ---------------------------------------------------------------------

// Índice del párrafo que contiene la selección; si no hay selección,
// el primer párrafo visible en pantalla ("desde aquí" literal).
function paragraphFromSelectionOrView() {
  const sel = window.getSelection();
  if (sel && !sel.isCollapsed && sel.anchorNode) {
    let node = sel.anchorNode;
    if (node.nodeType === Node.TEXT_NODE) node = node.parentElement;
    const p = node && node.closest ? node.closest("#doc p[data-i]") : null;
    if (p) return parseInt(p.dataset.i, 10);
  }
  const top = $("toolbar").getBoundingClientRect().bottom;
  for (const p of document.querySelectorAll("#doc p[data-i]")) {
    if (p.getBoundingClientRect().bottom > top + 4) {
      return parseInt(p.dataset.i, 10);
    }
  }
  return 0;
}

async function readFrom(index) {
  const a = api();
  const tab = findTab(state.active);
  if (!a || !tab || tab.error || !tab.paragraphs.length) return;
  clearReading();
  state.readingPath = tab.path;
  await a.read_document(tab.path, index);
}

async function readSelection() {
  const a = api();
  if (!a) return;
  const text = String(window.getSelection() || "").trim();
  if (!text) return;
  clearReading();
  await a.read_text(text);
}

function applyHighlight(index, smooth) {
  for (const el of document.querySelectorAll("#doc p.reading")) {
    el.classList.remove("reading");
  }
  const p = document.querySelector(`#doc p[data-i="${index}"]`);
  if (p) {
    p.classList.add("reading");
    p.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "center" });
  }
}

function clearReading() {
  state.readingPath = null;
  state.readingIndex = -1;
  for (const el of document.querySelectorAll("#doc p.reading")) {
    el.classList.remove("reading");
  }
}

// Callbacks que invoca Python (bridge.py) vía evaluate_js.
window.lv = {
  onParagraph(index) {
    state.readingIndex = index;
    // resaltar solo si la pestaña activa es la que está sonando
    if (state.readingPath && state.readingPath === state.active) {
      applyHighlight(index, true);
    }
  },
  onEnd() {
    clearReading();
  },
  // Archivo soltado sobre la ventana (app.py inyecta la ruta real).
  openDropped(path) {
    openPath(path);
  },
};

// --- arranque ---------------------------------------------------------------------

async function boot() {
  const a = api();
  if (!a) return;
  const data = await a.get_boot();
  applyStrings(data.strings);
  renderRecents(data.recents);
  if (data.initial) addOrUpdateTab(normalizeDoc(data.initial));
}

function wireUi() {
  $("open-file").addEventListener("click", openDialog);
  $("read-all").addEventListener("click", () => {
    window.getSelection()?.removeAllRanges();
    readFrom(0);
  });
  $("read-here").addEventListener("click", () =>
    readFrom(paragraphFromSelectionOrView())
  );
  $("read-sel").addEventListener("click", readSelection);
  $("stop").addEventListener("click", async () => {
    const a = api();
    if (a) await a.stop();
    clearReading();
  });

  const setFont = (delta) => {
    const cur = parseFloat(
      getComputedStyle(document.documentElement).getPropertyValue("--font-size")
    );
    const next = Math.min(40, Math.max(14, cur + delta));
    document.documentElement.style.setProperty("--font-size", `${next}px`);
    try {
      localStorage.setItem("lv-font-size", String(next));
    } catch (e) { /* almacenamiento no disponible: no es crítico */ }
  };
  $("font-plus").addEventListener("click", () => setFont(2));
  $("font-minus").addEventListener("click", () => setFont(-2));
  try {
    const saved = parseFloat(localStorage.getItem("lv-font-size"));
    if (saved >= 14 && saved <= 40) {
      document.documentElement.style.setProperty("--font-size", `${saved}px`);
    }
  } catch (e) { /* idem */ }

  // Feedback visual al arrastrar; la ruta real la entrega pywebview desde
  // Python (app.py), porque el DOM no expone rutas de archivos.
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
  });
}

document.addEventListener("DOMContentLoaded", () => {
  wireUi();
  if (api()) boot();
  else window.addEventListener("pywebviewready", boot, { once: true });
});
