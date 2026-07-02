from .base import TTSBackend
from .piper_backend import PiperBackend

__all__ = ["TTSBackend", "PiperBackend", "get_backend"]


def get_backend(engine: str, voices_dir, use_gpu: bool = False) -> TTSBackend:
    if engine == "piper":
        return PiperBackend(voices_dir, use_gpu=use_gpu)
    if engine == "kokoro":
        from .kokoro_backend import KokoroBackend

        return KokoroBackend(voices_dir, use_gpu=use_gpu)
    raise ValueError(f"Motor desconocido: {engine!r}")
