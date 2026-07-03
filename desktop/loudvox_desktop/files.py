"""Extracción de texto de archivos: PDF, txt, md, djvu."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


class NoTextLayerError(ValueError):
    """El documento es un escaneo/imagen sin capa de texto extraíble."""


class MissingToolError(RuntimeError):
    """Falta una herramienta del sistema (p. ej. djvulibre para .djvu)."""


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

    if suffix == ".djvu":
        return _extract_djvu(path)

    raise ValueError(
        f"Formato no soportado: {suffix or '(sin extensión)'}. "
        "Soportados: .pdf .txt .md .djvu"
    )


def _extract_djvu(path: Path) -> str:
    """Extrae la capa de texto de un DJVU con ``djvutxt`` (djvulibre).

    Un DJVU escaneado sin OCR no tiene capa de texto: djvutxt devuelve
    vacío con exit 0 (verificado contra djvulibre real). En ese caso se
    lanza NoTextLayerError con un mensaje claro para la UI.
    """
    tool = shutil.which("djvutxt")
    if tool is None:
        raise MissingToolError(
            "Para leer .djvu hace falta djvulibre (comando djvutxt). "
            "Windows: https://djvu.sourceforge.net / "
            "Linux: sudo apt install djvulibre-bin"
        )
    result = subprocess.run(
        [tool, str(path)], capture_output=True, timeout=120
    )
    if result.returncode != 0:
        raise ValueError(
            f"djvutxt no pudo leer el archivo: "
            f"{result.stderr.decode(errors='replace').strip()[:200]}"
        )
    text = result.stdout.decode("utf-8", errors="replace").strip()
    if not text:
        raise NoTextLayerError(
            "Este DJVU es un escaneo sin capa de texto: no hay nada que "
            "leer en voz alta. (Haría falta pasarle OCR primero.)"
        )
    return text


# Línea que termina oración (para decidir cortes de párrafo)
_SENT_END = re.compile(r"[.!?…:]['\"»)\]]?\s*$")
_STARTS_UPPER = re.compile(r"^\s*[¿¡\"«(\[]?[A-ZÁÉÍÓÚÜÑ0-9]")


def to_paragraphs(text: str) -> list[str]:
    """Reconstruye párrafos legibles a partir de texto crudo.

    Los PDF (pypdf) y djvutxt devuelven una línea por renglón VISUAL, no
    por párrafo. Heurística (portada del pageToParagraphs de
    extension/viewer.js): línea en blanco = corte seguro; renglón que
    termina oración seguido de renglón que empieza con mayúscula = corte;
    el resto se une con espacio.
    """
    paragraphs: list[str] = []
    current = ""
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            if current:
                paragraphs.append(current)
                current = ""
            continue
        if current and _SENT_END.search(current) and _STARTS_UPPER.match(line):
            paragraphs.append(current)
            current = line
        else:
            current = f"{current} {line}".strip()
    if current:
        paragraphs.append(current)
    # descartar restos no legibles (números de página sueltos, etc.)
    return [p for p in paragraphs if len(p) >= 2]


def extract_paragraphs(path: str | Path) -> list[str]:
    """Extrae el documento como lista de párrafos listos para mostrar/leer."""
    return to_paragraphs(extract_text(path))


def find_start(text: str, phrase: str) -> str:
    """Devuelve el texto desde la primera aparición de ``phrase`` (sin
    distinguir mayúsculas). Si no aparece, devuelve el texto completo."""
    idx = text.lower().find(phrase.lower())
    return text[idx:] if idx >= 0 else text
