// LoudVox service worker: orquesta lectura entre la pestaña activa,
// el documento offscreen (audio) y el motor local (http://127.0.0.1:5089).

const ENGINE = "http://127.0.0.1:5089";
let currentTabId = null;

async function ensureOffscreen() {
  const has = await chrome.offscreen.hasDocument();
  if (!has) {
    await chrome.offscreen.createDocument({
      url: "offscreen.html",
      reasons: ["AUDIO_PLAYBACK"],
      justification: "Reproducir el audio de la lectura en voz alta",
    });
  }
}

async function getSettings() {
  const defaults = { language: "es", voice: "", speed: 1.0 };
  const stored = await chrome.storage.local.get(defaults);
  return { ...defaults, ...stored };
}

async function startReading(mode, tabId) {
  const tab =
    tabId != null
      ? await chrome.tabs.get(tabId)
      : (await chrome.tabs.query({ active: true, currentWindow: true }))[0];
  if (!tab || !tab.id) return;
  currentTabId = tab.id;

  let collected;
  try {
    collected = await chrome.tabs.sendMessage(tab.id, {
      type: "lv-collect",
      mode,
    });
  } catch (e) {
    // Página sin content script (chrome://, PDF viewer, etc.)
    console.warn("LoudVox: no se pudo leer esta página:", e.message);
    return;
  }
  const blocks = (collected?.blocks || []).map((b) => b.text).filter(Boolean);
  if (blocks.length === 0) return;

  const settings = await getSettings();
  await ensureOffscreen();
  chrome.runtime.sendMessage({
    type: "lv-play",
    target: "offscreen",
    blocks,
    settings,
    highlight: mode === "from-here",
  });
}

async function stopReading() {
  chrome.runtime.sendMessage({ type: "lv-stop", target: "offscreen" });
  if (currentTabId != null) {
    try {
      await chrome.tabs.sendMessage(currentTabId, { type: "lv-clear" });
    } catch (_) {}
  }
}

chrome.commands.onCommand.addListener((command) => {
  if (command === "read-selection") startReading("selection");
  else if (command === "read-from-here") startReading("from-here");
  else if (command === "stop-reading") stopReading();
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.target === "background") {
    if (msg.type === "lv-progress" && currentTabId != null && msg.highlight) {
      chrome.tabs
        .sendMessage(currentTabId, { type: "lv-highlight", index: msg.index })
        .catch(() => {});
    } else if (msg.type === "lv-ended" && currentTabId != null) {
      chrome.tabs.sendMessage(currentTabId, { type: "lv-clear" }).catch(() => {});
    } else if (msg.type === "lv-start") {
      startReading(msg.mode, msg.tabId).then(() => sendResponse({}));
      return true; // respuesta asíncrona
    } else if (msg.type === "lv-stop") {
      stopReading().then(() => sendResponse({}));
      return true;
    }
  }
  return false;
});
