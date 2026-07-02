from .base import TTSBackend
from .piper_backend import PiperBackend

__all__ = ["TTSBackend", "PiperBackend", "get_backend"]


def get_backend(engine: str, voices_dir, use_gpu: bool = False) -> TTSBackend:
    if engine == "piper":
        return PiperBackend(voices_dir, use_gpu=use_gpu)
    if engine == "kokoro":
        raise NotImplementedError(
            "El motor Kokoro llega en la Fase 5. Usá engine='piper'."
        )
    raise ValueError(f"Motor desconocido: {engine!r}")
