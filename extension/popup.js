// LoudVox popup: estado del motor, ajustes (idioma/voz/velocidad) y acciones.

const ENGINE = "http://127.0.0.1:5089";
const $ = (id) => document.getElementById(id);

async function loadSettings() {
  const defaults = { language: "es", voice: "", speed: 1.0 };
  const s = await chrome.storage.local.get(defaults);
  $("language").value = s.language;
  $("speed").value = s.speed;
  $("speed-val").textContent = `${Number(s.speed).toFixed(1)}×`;
  return s;
}

function saveSettings() {
  chrome.storage.local.set({
    language: $("language").value,
    voice: $("voice").value,
    speed: Number($("speed").value),
  });
}

async function refreshEngine(selectedVoice) {
  const dot = $("dot");
  const text = $("status-text");
  try {
    const health = await fetch(`${ENGINE}/health`).then((r) => r.json());
    const voices = await fetch(`${ENGINE}/voices`).then((r) => r.json());
    dot.className = "dot ok";
    text.textContent = `Motor activo (v${health.version})`;
    const sel = $("voice");
    sel.innerHTML = '<option value="">(por defecto del idioma)</option>';
    for (const v of voices.voices) {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      sel.appendChild(opt);
    }
    if (selectedVoice) sel.value = selectedVoice;
  } catch (_) {
    dot.className = "dot err";
    text.textContent = "Motor no encontrado. Ejecutá: loudvox serve";
  }
}

function sendToBackground(msg) {
  return chrome.runtime.sendMessage({ ...msg, target: "background" });
}

document.addEventListener("DOMContentLoaded", async () => {
  const s = await loadSettings();
  await refreshEngine(s.voice);

  $("language").addEventListener("change", saveSettings);
  $("voice").addEventListener("change", saveSettings);
  $("speed").addEventListener("input", () => {
    $("speed-val").textContent = `${Number($("speed").value).toFixed(1)}×`;
    saveSettings();
  });

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  $("read-selection").addEventListener("click", () => {
    sendToBackground({ type: "lv-start", mode: "selection", tabId: tab?.id });
    window.close();
  });
  $("read-from-here").addEventListener("click", () => {
    sendToBackground({ type: "lv-start", mode: "from-here", tabId: tab?.id });
    window.close();
  });
  $("stop").addEventListener("click", () => {
    sendToBackground({ type: "lv-stop" });
  });
});
