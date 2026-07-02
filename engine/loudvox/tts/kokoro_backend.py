"""Backend Kokoro (kokoro-onnx): voz de alta calidad, CPU-friendly.

Modelo de 82M parámetros (~310 MB) + banco de voces (~27 MB), en
``voices_dir``:  kokoro-v1.0.onnx  +  voices-v1.0.bin

Voces por idioma (prefijo = idioma, segunda letra = género f/m):
  es: ef_dora, em_alex, em_santa
  en: af_heart, af_bella, am_michael, bf_emma (británico), …
  it: if_sara, im_nicola
  (alemán no disponible en Kokoro v1.0: usar Piper para de)
"""

from __future__ import annotations

import io
import wave
from pathlib import Path

from .base import TTSBackend

MODEL_FILE = "kokoro-v1.0.onnx"
VOICES_FILE = "voices-v1.0.bin"

# Primera letra del nombre de voz -> código de idioma del fonemizador
_LANG_BY_PREFIX = {
    "a": "en-us",
    "b": "en-gb",
    "e": "es",
    "f": "fr-fr",
    "i": "it",
    "j": "ja",
    "p": "pt-br",
    "z": "zh",
}


class KokoroBackend(TTSBackend):
    def __init__(self, voices_dir: str | Path, use_gpu: bool = False):
        self.voices_dir = Path(voices_dir)
        self.use_gpu = use_gpu  # kokoro-onnx usa los providers de onnxruntime
        self._model = None

    def _load(self):
        if self._model is None:
            model = self.voices_dir / MODEL_FILE
            voices = self.voices_dir / VOICES_FILE
            if not model.exists() or not voices.exists():
                raise FileNotFoundError(
                    f"Faltan los archivos de Kokoro en {self.voices_dir}:\n"
                    f"  {MODEL_FILE} (~310 MB) y {VOICES_FILE} (~27 MB)\n"
                    f"Descargalos con: loudvox download kokoro"
                )
            from kokoro_onnx import Kokoro  # import diferido

            self._model = Kokoro(str(model), str(voices))
        return self._model

    def synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        volume: float = 1.0,
        speaker: int | None = None,
    ) -> bytes:
        import numpy as np

        if not 0.25 <= speed <= 4.0:
            raise ValueError(f"Velocidad fuera de rango [0.25, 4.0]: {speed}")
        if not 0.1 <= volume <= 2.0:
            raise ValueError(f"Volumen fuera de rango [0.1, 2.0]: {volume}")
        model = self._load()
        lang = _LANG_BY_PREFIX.get(voice[:1].lower(), "en-us")
        # Kokoro acepta speed 0.5-2.0; recortar sin fallar
        kspeed = min(2.0, max(0.5, speed))
        samples, rate = model.create(text, voice=voice, speed=kspeed, lang=lang)
        samples = np.clip(samples * volume * 32767.0, -32768, 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(samples.tobytes())
        return buf.getvalue()

    def list_voices(self) -> list[str]:
        model_ok = (self.voices_dir / MODEL_FILE).exists() and (
            self.voices_dir / VOICES_FILE
        ).exists()
        if not model_ok:
            return []
        try:
            return sorted(self._load().get_voices())
        except Exception:
            return []
