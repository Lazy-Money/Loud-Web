// LoudVox content script: extrae texto de la página y resalta lo que se lee.
// No envía nada a ningún servidor: solo responde mensajes del service worker.

(() => {
  const HIGHLIGHT_CLASS = "loudvox-reading";
  const SKIP_TAGS = new Set([
    "SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "IFRAME", "SVG", "CANVAS",
    "NAV", "HEADER", "FOOTER", "ASIDE", "BUTTON", "SELECT", "TEXTAREA", "INPUT",
  ]);
  const BLOCK_SELECTOR =
    "p, h1, h2, h3, h4, h5, h6, li, blockquote, pre, td, th, dd, dt, figcaption, article, section, div";
  const MAX_BLOCKS = 2000;

  let taggedElements = [];

  function isVisible(el) {
    const style = getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;
    return true;
  }

  function isSkippable(el) {
    for (let n = el; n && n !== document.body; n = n.parentElement) {
      if (SKIP_TAGS.has(n.tagName)) return true;
      if (n.getAttribute && n.getAttribute("aria-hidden") === "true") return true;
    }
    return false;
  }

  // Bloques "hoja": elementos de bloque que no contienen otros bloques con texto.
  function leafBlocks(root) {
    const all = root.querySelectorAll(BLOCK_SELECTOR);
    const blocks = [];
    for (const el of all) {
      if (blocks.length >= MAX_BLOCKS) break;
      if (isSkippable(el) || !isVisible(el)) continue;
      const hasBlockChild = el.querySelector(BLOCK_SELECTOR) !== null;
      if (hasBlockChild) continue;
      const text = el.innerText.replace(/\s+/g, " ").trim();
      if (text.length < 2) continue;
      blocks.push({ el, text });
    }
    return blocks;
  }

  function clearHighlight() {
    for (const el of taggedElements) el.classList.remove(HIGHLIGHT_CLASS);
    taggedElements = [];
  }

  function collect(mode) {
    clearHighlight();
    // Visor de PDF nativo: acá no hay texto accesible; avisar al service
    // worker para que redirija al lector LoudVox.
    if (document.contentType === "application/pdf") {
      return { pdf: true, url: location.href };
    }
    const sel = window.getSelection();

    if (mode === "selection") {
      const text = sel ? sel.toString().trim() : "";
      if (!text) return { blocks: [] };
      return { blocks: [{ text }] }; // sin resaltado: es lo que el usuario marcó
    }

    // "from-here": todos los bloques desde la selección hasta el final.
    // "page": la página completa, ignorando cualquier selección.
    const blocks = leafBlocks(document.body);
    let startIdx = 0;
    if (mode === "from-here" && sel && sel.rangeCount > 0 && sel.anchorNode) {
      const anchor = sel.getRangeAt(0).startContainer;
      const anchorEl =
        anchor.nodeType === Node.ELEMENT_NODE ? anchor : anchor.parentElement;
      if (anchorEl) {
        for (let i = 0; i < blocks.length; i++) {
          if (blocks[i].el === anchorEl || blocks[i].el.contains(anchorEl)) {
            startIdx = i;
            break;
          }
        }
      }
    }
    const chosen = blocks.slice(startIdx);
    taggedElements = chosen.map((b) => b.el);
    return { blocks: chosen.map((b) => ({ text: b.text })) };
  }

  function highlight(index) {
    for (const el of taggedElements) el.classList.remove(HIGHLIGHT_CLASS);
    const el = taggedElements[index];
    if (el) {
      el.classList.add(HIGHLIGHT_CLASS);
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.type === "lv-collect") {
      sendResponse(collect(msg.mode));
    } else if (msg.type === "lv-highlight") {
      highlight(msg.index);
      sendResponse({});
    } else if (msg.type === "lv-clear") {
      clearHighlight();
      sendResponse({});
    }
    return false;
  });
})();
