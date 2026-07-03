"""Puente Python↔JS del visor (js_api de pywebview).

Contrato (lo que JS puede llamar en ``window.pywebview.api``):
  get_boot()                -> {strings, recents, initial}  (al cargar la UI)
  open_file_dialog()        -> doc | None   (diálogo nativo de archivo)
  open_path(path)           -> doc          (doc = {ok, path, title, paragraphs} o {ok:False, error})
  read_document(path, i)    -> {ok}         (lee desde el párrafo i)
  read_text(texto)          -> {ok}         (lee un texto arbitrario: la selección)
  stop()                    -> {ok}
  get_recents()             -> [{path, title}]

Python → JS (via evaluate_js): lv.onParagraph(i), lv.onEnd().
"""

from __future__ import annotations

import threading
from pathlib import Path

from loudvox.config import load as load_config

from ..files import extract_paragraphs
from ..i18n import strings_for
from . import recents
from .reader import ParagraphReader


class ViewerApi:
    def __init__(self, initial_path: str | None = None):
        self.cfg = load_config()
        self._window = None  # se setea después de create_window
        self._docs: dict[str, list[str]] = {}  # cache path -> párrafos
        self._initial_path = initial_path
        self._reader: ParagraphReader | None = None
        self._reader_lock = threading.Lock()

    # ---- infraestructura -------------------------------------------------

    def set_window(self, window) -> None:
        self._window = window

    def _js(self, script: str) -> None:
        if self._window is not None:
            try:
                self._window.evaluate_js(script)
            except Exception:
                pass  # la ventana puede estar cerrándose

    def _get_reader(self) -> ParagraphReader:
        # Carga diferida: la primera lectura carga el modelo de voz
        with self._reader_lock:
            if self._reader is None:
                self._reader = ParagraphReader(
                    self.cfg,
                    on_paragraph=lambda i: self._js(f"lv.onParagraph({i})"),
                    on_end=lambda: self._js("lv.onEnd()"),
                )
            return self._reader

    # ---- API expuesta a JS -------------------------------------------------

    def get_boot(self):
        lang = self.cfg.resolved_ui_language()
        initial = None
        if self._initial_path:
            initial = self.open_path(self._initial_path)
            self._initial_path = None
        return {
            "strings": strings_for(lang),
            "recents": recents.existing(),
            "initial": initial,
        }

    def open_file_dialog(self):
        import webview

        if self._window is None:
            return None
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=("Documentos (*.pdf;*.txt;*.md;*.djvu)", "Todos (*.*)"),
        )
        if not result:
            return None
        return self.open_path(result[0])

    def open_path(self, path: str):
        p = Path(path)
        try:
            paragraphs = extract_paragraphs(p)
        except Exception as exc:
            return {"ok": False, "path": str(p), "title": p.name,
                    "error": str(exc)}
        self._docs[str(p)] = paragraphs
        recents.add(str(p), p.name)
        return {"ok": True, "path": str(p), "title": p.name,
                "paragraphs": paragraphs}

    def read_document(self, path: str, start_index: int = 0):
        paragraphs = self._docs.get(path)
        if paragraphs is None:
            doc = self.open_path(path)
            if not doc.get("ok"):
                return {"ok": False, "error": doc.get("error", "")}
            paragraphs = doc["paragraphs"]
        try:
            self._get_reader().read(paragraphs, start_index=int(start_index))
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True}

    def read_text(self, text: str):
        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "empty"}
        try:
            self._get_reader().read([text])
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True}

    def stop(self):
        if self._reader is not None:
            self._reader.stop()
        return {"ok": True}

    def get_recents(self):
        return recents.existing()
