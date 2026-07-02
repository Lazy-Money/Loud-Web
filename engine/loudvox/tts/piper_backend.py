"""Backend Piper: síntesis rápida en CPU, con opción GPU (CUDA).

Cada voz es un par de archivos en ``voices_dir``:
  <nombre>.onnx  +  <nombre>.onnx.json
"""

from __future__ import annotations

import io
import wave
from pathlib import Path

from .base import TTSBackend


class PiperBackend(TTSBackend):
    def __init__(self, voices_dir: str | Path, use_gpu: bool = False):
        self.voices_dir = Path(voices_dir)
        self.use_gpu = use_gpu
        self._loaded: dict[str, object] = {}  # cache de modelos en memoria

    def _voice_path(self, voice: str) -> Path:
        path = self.voices_dir / f"{voice}.onnx"
        if not path.exists():
            available = ", ".join(self.list_voices()) or "(ninguna)"
            raise FileNotFoundError(
                f"Voz {voice!r} no encontrada en {self.voices_dir}.\n"
                f"Voces instaladas: {available}\n"
                f"Descargala con: loudvox download {voice}"
            )
        return path

    def _load(self, voice: str):
        if voice not in self._loaded:
            from piper import PiperVoice  # import diferido: arranque más rápido

            self._loaded[voice] = PiperVoice.load(
                self._voice_path(voice), use_cuda=self.use_gpu
            )
        return self._loaded[voice]

    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> bytes:
        from piper import SynthesisConfig

        if not 0.25 <= speed <= 4.0:
            raise ValueError(f"Velocidad fuera de rango [0.25, 4.0]: {speed}")
        model = self._load(voice)
        # En Piper, length_scale es la duración de los fonemas: la inversa
        # de la velocidad percibida.
        syn = SynthesisConfig(length_scale=1.0 / speed)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            model.synthesize_wav(text, wav_file, syn_config=syn)
        return buf.getvalue()

    def list_voices(self) -> list[str]:
        if not self.voices_dir.exists():
            return []
        return sorted(
            p.name[: -len(".onnx")]
            for p in self.voices_dir.glob("*.onnx")
            if p.with_suffix(".onnx.json").exists()
            or Path(f"{p}.json").exists()
        )
