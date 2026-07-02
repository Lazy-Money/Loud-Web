"""Catálogo de voces instaladas, con metadatos legibles para las UIs.

Cada entrada:
  {"id": "es_ES-sharvard-medium", "engine": "piper", "lang": "es",
   "region": "España", "name": "Sharvard", "gender": "F", "speaker": 0,
   "label": "España — Sharvard (femenino)"}

Para voces Piper multi-hablante (p. ej. sharvard) se genera una entrada por
hablante, leyendo ``speaker_id_map`` del ``.onnx.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

REGION_NAMES = {
    "es_ES": ("es", "España"),
    "es_MX": ("es", "México"),
    "es_AR": ("es", "Argentina"),
    "en_US": ("en", "EE. UU."),
    "en_GB": ("en", "Reino Unido"),
    "it_IT": ("it", "Italia"),
    "de_DE": ("de", "Alemania"),
}

# Género por nombre de dataset Piper (solo los confirmados; el resto sin dato)
_PIPER_GENDER = {
    "davefx": "M",
    "claude": "F",  # es_MX, confirmado a oído
    "ald": "M",  # es_MX, confirmado a oído
    "amy": "F",
    "alan": "M",
    "paola": "F",
    "riccardo": "M",
    "thorsten": "M",
    "eva_k": "F",
}

_GENDER_WORD = {"F": "femenino", "M": "masculino"}

# Voces Kokoro conocidas para nuestros idiomas (prefijo: idioma+género)
_KOKORO_VOICES = [
    ("ef_dora", "es", "España", "Dora", "F"),
    ("em_alex", "es", "España", "Alex", "M"),
    ("em_santa", "es", "España", "Santa", "M"),
    ("af_heart", "en", "EE. UU.", "Heart", "F"),
    ("af_bella", "en", "EE. UU.", "Bella", "F"),
    ("am_michael", "en", "EE. UU.", "Michael", "M"),
    ("bf_emma", "en", "Reino Unido", "Emma", "F"),
    ("bm_george", "en", "Reino Unido", "George", "M"),
    ("if_sara", "it", "Italia", "Sara", "F"),
    ("im_nicola", "it", "Italia", "Nicola", "M"),
]


def _label(region: str, name: str, gender: str | None) -> str:
    g = f" ({_GENDER_WORD[gender]})" if gender in _GENDER_WORD else ""
    return f"{region} — {name}{g}"


def _piper_entries(voices_dir: Path) -> list[dict]:
    entries = []
    for onnx in sorted(voices_dir.glob("*.onnx")):
        cfg_path = Path(f"{onnx}.json")
        if not cfg_path.exists():
            cfg_path = onnx.with_suffix(".onnx.json")
        if not cfg_path.exists() or onnx.name.startswith("kokoro"):
            continue
        voice_id = onnx.name[: -len(".onnx")]
        try:
            meta = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
        locale = (meta.get("language") or {}).get("code") or voice_id.split("-")[0]
        lang, region = REGION_NAMES.get(locale, (locale.split("_")[0], locale))
        dataset = meta.get("dataset") or (
            voice_id.split("-")[1] if "-" in voice_id else voice_id
        )
        name = dataset.replace("_", " ").title()
        speaker_map = meta.get("speaker_id_map") or {}

        if len(speaker_map) > 1:
            for key, sid in sorted(speaker_map.items(), key=lambda kv: kv[1]):
                gender = key.upper() if key.upper() in _GENDER_WORD else None
                spk_name = name if gender else f"{name} {key}"
                entries.append(
                    {
                        "id": voice_id,
                        "engine": "piper",
                        "lang": lang,
                        "region": region,
                        "name": spk_name,
                        "gender": gender,
                        "speaker": sid,
                        "label": _label(region, spk_name, gender),
                    }
                )
        else:
            gender = _PIPER_GENDER.get(dataset)
            entries.append(
                {
                    "id": voice_id,
                    "engine": "piper",
                    "lang": lang,
                    "region": region,
                    "name": name,
                    "gender": gender,
                    "speaker": None,
                    "label": _label(region, name, gender),
                }
            )
    return entries


def _kokoro_entries(voices_dir: Path) -> list[dict]:
    from .tts.kokoro_backend import MODEL_FILE, VOICES_FILE

    if not (voices_dir / MODEL_FILE).exists() or not (voices_dir / VOICES_FILE).exists():
        return []
    return [
        {
            "id": vid,
            "engine": "kokoro",
            "lang": lang,
            "region": region,
            "name": name,
            "gender": gender,
            "speaker": None,
            "label": _label(region, name, gender),
        }
        for vid, lang, region, name, gender in _KOKORO_VOICES
    ]


def list_catalog(voices_dir: str | Path) -> list[dict]:
    """Todas las voces instaladas (ambos motores), con metadatos."""
    voices_dir = Path(voices_dir)
    if not voices_dir.exists():
        return []
    return _piper_entries(voices_dir) + _kokoro_entries(voices_dir)
