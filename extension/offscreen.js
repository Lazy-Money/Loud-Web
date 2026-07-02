// LoudVox offscreen: pide el audio al motor local y lo reproduce.
// Cola por bloques con prefetch del siguiente para lectura sin cortes.

const ENGINE = "http://127.0.0.1:5089";

let session = 0; // se incrementa en cada play/stop para invalidar sesiones viejas
let currentAudio = null;

async function synthesize(text, settings) {
  const body = { text, speed: Number(settings.speed) || 1.0 };
  if (settings.voice) body.voice = settings.voice;
  if (settings.language) body.language = settings.language;
  if (settings.volume != null) body.volume = Number(settings.volume) || 1.0;
  if (settings.pitch != null && Number(settings.pitch) !== 0)
    body.pitch = Number(settings.pitch);
  const resp = await fetch(`${ENGINE}/speak`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.error || `Motor respondió ${resp.status}`);
  }
  const blob = await resp.blob();
  return URL.createObjectURL(blob);
}

function playUrl(url) {
  return new Promise((resolve, reject) => {
    const audio = new Audio(url);
    currentAudio = audio;
    audio.onended = () => resolve();
    audio.onerror = () => reject(new Error("Error de reproducción"));
    audio.play().catch(reject);
  });
}

async function playBlocks(blocks, settings, highlight) {
  const mySession = ++session;
  let played = 0;
  let lastError = "";
  let next = synthesize(blocks[0], settings);

  for (let i = 0; i < blocks.length; i++) {
    let url = null;
    try {
      url = await next;
    } catch (e) {
      lastError = e.message;
      console.warn("LoudVox: fallo al sintetizar bloque", i, e.message);
    }
    // Prefetch del siguiente bloque mientras suena el actual.
    next = i + 1 < blocks.length ? synthesize(blocks[i + 1], settings) : null;
    if (next) next.catch(() => {}); // evitar 'unhandled rejection' si se detiene

    if (mySession !== session) {
      if (url) URL.revokeObjectURL(url);
      return; // detenido o reemplazado por otra lectura
    }
    if (!url) continue; // este bloque falló: seguir con el próximo

    chrome.runtime.sendMessage({
      type: "lv-progress",
      target: "background",
      index: i,
      highlight,
    });
    try {
      await playUrl(url);
      played++;
    } catch (e) {
      console.warn("LoudVox: reproducción falló en bloque", i, e.message);
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  if (mySession === session) {
    if (played === 0) {
      const detail = lastError.includes("Failed to fetch")
        ? "Motor no encontrado. Ejecutá en una terminal: loudvox serve"
        : lastError || "Error desconocido";
      chrome.runtime.sendMessage({
        type: "lv-error",
        target: "background",
        message: `No se pudo reproducir: ${detail}`,
      });
    }
    chrome.runtime.sendMessage({ type: "lv-ended", target: "background" });
  }
}

function stop() {
  session++;
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.target !== "offscreen") return;
  if (msg.type === "lv-play") {
    stop();
    playBlocks(msg.blocks, msg.settings, msg.highlight);
  } else if (msg.type === "lv-stop") {
    stop();
  }
});
