"""Interfaz común para motores TTS."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TTSBackend(ABC):
    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        volume: float = 1.0,
        speaker: int | None = None,
    ) -> bytes:
        """Sintetiza ``text`` y devuelve un archivo WAV completo en bytes.

        ``speed``: 1.0 = normal, 2.0 = doble de rápido, 0.5 = mitad.
        ``volume``: 1.0 = normal, 0.5 = mitad, 2.0 = doble.
        ``speaker``: id de hablante en voces multi-hablante (None = default).
        """

    @abstractmethod
    def list_voices(self) -> list[str]:
        """Voces instaladas localmente y listas para usar."""
