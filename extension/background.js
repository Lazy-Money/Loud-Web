// LoudVox service worker: orquesta lectura entre la pestaña activa,
// el documento offscreen (audio) y el motor local (http://127.0.0.1:5089).

let currentTabId = null;

function notify(message) {
  chrome.notifications.create({
    type: "basic",
    iconUrl: "icons/icon128.png",
    title: "LoudVox",
    message,
  });
}

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

// Pide los bloques al content script; si no está (pestaña abierta antes de
// instalar la extensión), lo inyecta y reintenta.
async function collectFromTab(tabId, mode) {
  try {
    return await chrome.tabs.sendMessage(tabId, { type: "lv-collect", mode });
  } catch (_) {
    await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
    await chrome.scripting.insertCSS({ target: { tabId }, files: ["content.css"] });
    return await chrome.tabs.sendMessage(tabId, { type: "lv-collect", mode });
  }
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
    collected = await collectFromTab(tab.id, mode);
  } catch (e) {
    // ¿Es el visor de PDF nativo? Redirigir a nuestro lector y leer solo.
    if (tab.url && /\.pdf(\?|#|$)/i.test(tab.url)) {
      const viewer = chrome.runtime.getURL(
        `viewer.html?url=${encodeURIComponent(tab.url)}&autoread=1`
      );
      chrome.tabs.update(tab.id, { url: viewer });
      return;
    }
    // Página vedada para extensiones: brave://, chrome://, Web Store.
    notify(
      "No se puede leer esta página (las páginas internas del navegador " +
        "están bloqueadas para extensiones)."
    );
    return;
  }
  const blocks = (collected?.blocks || []).map((b) => b.text).filter(Boolean);
  if (blocks.length === 0) {
    if (mode === "selection") notify("No hay texto seleccionado.");
    return;
  }

  const settings = await getSettings();
  await ensureOffscreen();
  chrome.runtime.sendMessage({
    type: "lv-play",
    target: "offscreen",
    blocks,
    settings,
    highlight: mode !== "selection",
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

// --- Menú de clic derecho (complementa a las hotkeys, no las reemplaza) ----

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "lv-read-selection",
    title: "🔊 Leer selección",
    contexts: ["selection"],
  });
  chrome.contextMenus.create({
    id: "lv-read-from-here",
    title: "⏩ Leer desde aquí en adelante",
    contexts: ["selection"],
  });
  chrome.contextMenus.create({
    id: "lv-read-page",
    title: "🔊 Leer esta página completa",
    contexts: ["page"],
  });
  chrome.contextMenus.create({
    id: "lv-stop",
    title: "⏹ Detener lectura",
    contexts: ["page", "selection"],
  });
  chrome.contextMenus.create({
    id: "lv-open-pdf",
    title: "📖 Abrir PDF con el lector LoudVox",
    contexts: ["link"],
    targetUrlPatterns: ["*://*/*.pdf*", "*://*/*.PDF*", "file:///*.pdf"],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "lv-read-selection") startReading("selection", tab?.id);
  else if (info.menuItemId === "lv-read-from-here") startReading("from-here", tab?.id);
  else if (info.menuItemId === "lv-read-page") startReading("page", tab?.id);
  else if (info.menuItemId === "lv-stop") stopReading();
  else if (info.menuItemId === "lv-open-pdf" && info.linkUrl) {
    chrome.tabs.create({
      url: chrome.runtime.getURL(`viewer.html?url=${encodeURIComponent(info.linkUrl)}`),
    });
  }
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.target === "background") {
    if (msg.type === "lv-progress" && currentTabId != null && msg.highlight) {
      chrome.tabs
        .sendMessage(currentTabId, { type: "lv-highlight", index: msg.index })
        .catch(() => {});
    } else if (msg.type === "lv-ended" && currentTabId != null) {
      chrome.tabs.sendMessage(currentTabId, { type: "lv-clear" }).catch(() => {});
    } else if (msg.type === "lv-error") {
      notify(msg.message);
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
