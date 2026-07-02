"""Extracción de texto de archivos: PDF, txt, md."""

from __future__ import annotations

import re
from pathlib import Path


def _strip_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)  # bloques de código
    text = re.sub(r"`([^`]*)`", r"\1", text)  # código inline
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # imágenes
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # enlaces -> texto
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)  # títulos
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)  # viñetas
    text = re.sub(r"^\s*\|.*\|\s*$", " ", text, flags=re.M)  # tablas
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)  # énfasis
    text = re.sub(r"^>\s?", "", text, flags=re.M)  # citas
    return text


def extract_text(path: str | Path) -> str:
    """Devuelve el texto plano del archivo, listo para sintetizar."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}")
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        from pypdf import PdfReader  # import diferido

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)

    if suffix in (".txt", ".text", ".log"):
        return path.read_text(encoding="utf-8", errors="replace")

    if suffix in (".md", ".markdown"):
        return _strip_markdown(path.read_text(encoding="utf-8", errors="replace"))

    raise ValueError(
        f"Formato no soportado: {suffix or '(sin extensión)'}. "
        "Soportados: .pdf .txt .md"
    )


def find_start(text: str, phrase: str) -> str:
    """Devuelve el texto desde la primera aparición de ``phrase`` (sin
    distinguir mayúsculas). Si no aparece, devuelve el texto completo."""
    idx = text.lower().find(phrase.lower())
    return text[idx:] if idx >= 0 else text
