"""Configuración persistente de LoudVox.

Se guarda como JSON en el directorio de configuración del usuario:
  - Linux:   ~/.config/loudvox/config.json
  - Windows: %APPDATA%/loudvox/config.json
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

SUPPORTED_LANGUAGES = ["es", "en", "it", "de"]

# Voces Piper recomendadas por idioma. La primera es la usada por defecto.
RECOMMENDED_VOICES: dict[str, list[str]] = {
    "es": ["es_ES-davefx-medium", "es_MX-claude-high", "es_ES-sharvard-medium"],
    "en": ["en_US-lessac-medium", "en_GB-alan-medium", "en_US-amy-medium"],
    "it": ["it_IT-paola-medium", "it_IT-riccardo-x_low"],
    "de": ["de_DE-thorsten-medium", "de_DE-eva_k-x_low"],
}


def config_dir() -> Path:
    """Directorio de configuración según plataforma."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(base) / "loudvox"
    xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg) / "loudvox"


def data_dir() -> Path:
    """Directorio de datos (voces descargadas, diccionarios del usuario)."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(base) / "loudvox"
    xdg = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(xdg) / "loudvox"


@dataclass
class Hotkeys:
    """Combinaciones de teclas personalizables (2 o más teclas).

    Formato: teclas separadas por "+", p. ej. "ctrl+alt+r".
    La validación exige al menos 2 teclas; no se prohíbe ninguna combinación.
    """

    read_selection: str = "ctrl+alt+r"
    read_from_here: str = "ctrl+alt+f"
    dictate: str = "ctrl+alt+d"
    stop: str = "ctrl+alt+s"


@dataclass
class Config:
    language: str = "es"
    voice: str = ""  # vacío = primera voz recomendada del idioma
    speed: float = 1.0  # 0.5 (lento) a 3.0 (rápido)
    pitch: float = 0.0  # semitonos, negativo = más grave (Fase 5)
    use_gpu: bool = False  # onnxruntime CUDA si está disponible
    engine: str = "piper"  # "piper" | "kokoro" (Fase 5)
    voices_dir: str = ""  # vacío = data_dir()/voices
    hotkeys: Hotkeys = field(default_factory=Hotkeys)

    def resolved_voice(self) -> str:
        if self.voice:
            return self.voice
        return RECOMMENDED_VOICES[self.language][0]

    def resolved_voices_dir(self) -> Path:
        if self.voices_dir:
            return Path(self.voices_dir)
        return data_dir() / "voices"


def validate_hotkey(combo: str) -> None:
    """Exige combinaciones de al menos 2 teclas no vacías."""
    keys = [k.strip() for k in combo.lower().split("+")]
    if len(keys) < 2 or any(not k for k in keys):
        raise ValueError(
            f"Combinación inválida: {combo!r}. Se requieren al menos 2 teclas, "
            'p. ej. "ctrl+alt+r".'
        )


def load(path: Path | None = None) -> Config:
    path = path or (config_dir() / "config.json")
    if not path.exists():
        return Config()
    raw = json.loads(path.read_text(encoding="utf-8"))
    hotkeys = Hotkeys(**raw.pop("hotkeys", {}))
    known = {f for f in Config.__dataclass_fields__ if f != "hotkeys"}
    cfg = Config(**{k: v for k, v in raw.items() if k in known}, hotkeys=hotkeys)
    if cfg.language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Idioma no soportado: {cfg.language!r}. Opciones: {SUPPORTED_LANGUAGES}"
        )
    for combo in asdict(cfg.hotkeys).values():
        validate_hotkey(combo)
    return cfg


def save(cfg: Config, path: Path | None = None) -> Path:
    path = path or (config_dir() / "config.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(cfg), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return path
