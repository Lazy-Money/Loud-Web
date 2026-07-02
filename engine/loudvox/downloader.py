"""Descarga de voces Piper desde Hugging Face.

ÚNICO componente que usa la red, y solo cuando el usuario lo ejecuta
explícitamente (loudvox download). La síntesis nunca sale de tu máquina.
"""

from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path

from .config import RECOMMENDED_VOICES

_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def _voice_url(voice: str, ext: str) -> str:
    # es_ES-davefx-medium -> es/es_ES/davefx/medium/es_ES-davefx-medium.onnx
    locale, name, quality = voice.split("-", 2)
    lang = locale.split("_")[0]
    return f"{_BASE}/{lang}/{locale}/{name}/{quality}/{voice}{ext}"


def download_voice(voice: str, dest_dir: str | Path) -> Path:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    for ext in (".onnx.json", ".onnx"):
        dest = dest_dir / f"{voice}{ext}"
        if dest.exists():
            print(f"  ya existe: {dest.name}")
            continue
        url = _voice_url(voice, ext)
        print(f"  bajando {dest.name} ...")
        tmp = dest.with_suffix(dest.suffix + ".part")
        with urllib.request.urlopen(url) as resp, tmp.open("wb") as fh:
            shutil.copyfileobj(resp, fh)
        tmp.rename(dest)
    return dest_dir / f"{voice}.onnx"


def download_language(lang: str, dest_dir: str | Path) -> list[Path]:
    """Descarga todas las voces recomendadas de un idioma."""
    if lang not in RECOMMENDED_VOICES:
        raise ValueError(
            f"Idioma no soportado: {lang!r}. Opciones: {list(RECOMMENDED_VOICES)}"
        )
    return [download_voice(v, dest_dir) for v in RECOMMENDED_VOICES[lang]]
