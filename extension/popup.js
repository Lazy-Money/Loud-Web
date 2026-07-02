// LoudVox popup: estado del motor, ajustes (idioma/voz/velocidad) y acciones.

const ENGINE = "http://127.0.0.1:5089";
const $ = (id) => document.getElementById(id);

function pitchLabel(v) {
  const n = Number(v);
  if (n === 0) return "normal";
  return n < 0 ? `${n} (grave)` : `+${n} (agudo)`;
}

function refreshLabels() {
  $("speed-val").textContent = `${Number($("speed").value).toFixed(1)}×`;
  $("volume-val").textContent = `${Math.round($("volume").value * 100)}%`;
  $("pitch-val").textContent = pitchLabel($("pitch").value);
}

async function loadSettings() {
  const defaults = { language: "es", voice: "", speed: 1.0, volume: 1.0, pitch: 0 };
  const s = await chrome.storage.local.get(defaults);
  $("language").value = s.language;
  $("speed").value = s.speed;
  $("volume").value = s.volume;
  $("pitch").value = s.pitch;
  refreshLabels();
  return s;
}

function saveSettings() {
  const [voiceId, speaker] = ($("voice").value || "|").split("|");
  chrome.storage.local.set({
    language: $("language").value,
    voice: voiceId,
    speaker: speaker === "" ? null : Number(speaker),
    speed: Number($("speed").value),
    volume: Number($("volume").value),
    pitch: Number($("pitch").value),
  });
}

let catalog = [];
let activeEngine = "piper";

function fillVoices(selectedValue) {
  const sel = $("voice");
  const lang = $("language").value;
  sel.innerHTML = '<option value="">(por defecto del idioma)</option>';
  for (const e of catalog) {
    if (e.engine !== activeEngine || e.lang !== lang) continue;
    const opt = document.createElement("option");
    opt.value = `${e.id}|${e.speaker ?? ""}`;
    opt.textContent = e.label;
    sel.appendChild(opt);
  }
  if (selectedValue) sel.value = selectedValue;
  if (!sel.value) sel.selectedIndex = 0;
}

async function refreshEngine(stored) {
  const dot = $("dot");
  const text = $("status-text");
  try {
    const health = await fetch(`${ENGINE}/health`).then((r) => r.json());
    const info = await fetch(`${ENGINE}/voices`).then((r) => r.json());
    dot.className = "dot ok";
    text.textContent = `Motor activo (v${health.version})`;
    catalog = info.catalog || [];
    activeEngine = info.engine || "piper";
    const storedValue = stored.voice
      ? `${stored.voice}|${stored.speaker ?? ""}`
      : "";
    fillVoices(storedValue);
  } catch (_) {
    dot.className = "dot err";
    text.textContent = "Motor no encontrado. Ejecutá: loudvox-desktop";
  }
}

const SAMPLES = {
  es: "Hola, así voy a sonar cuando lea para vos.",
  en: "Hello, this is how I will sound when reading.",
  it: "Ciao, ecco come suonerò durante la lettura.",
  de: "Hallo, so werde ich beim Vorlesen klingen.",
};

function sendToBackground(msg) {
  return chrome.runtime.sendMessage({ ...msg, target: "background" });
}

document.addEventListener("DOMContentLoaded", async () => {
  const s = await loadSettings();
  await refreshEngine(s.voice);

  $("language").addEventListener("change", () => {
    fillVoices("");
    saveSettings();
  });
  $("voice").addEventListener("change", saveSettings);
  for (const id of ["speed", "volume", "pitch"]) {
    $(id).addEventListener("input", () => {
      refreshLabels();
      saveSettings();
    });
  }
  $("test-voice").addEventListener("click", () => {
    saveSettings();
    sendToBackground({
      type: "lv-test",
      sample: SAMPLES[$("language").value] || SAMPLES.es,
    });
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
  $("open-pdf").addEventListener("click", () => {
    // Si la pestaña actual ya es un PDF de internet, abrirlo directo
    const url =
      tab?.url && /^https?:.*\.pdf(\?|#|$)/i.test(tab.url)
        ? `viewer.html?url=${encodeURIComponent(tab.url)}`
        : "viewer.html";
    chrome.tabs.create({ url: chrome.runtime.getURL(url) });
    window.close();
  });
});
