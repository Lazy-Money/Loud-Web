"""Interfaz común para motores TTS."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TTSBackend(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> bytes:
        """Sintetiza ``text`` y devuelve un archivo WAV completo en bytes.

        ``speed``: 1.0 = normal, 2.0 = doble de rápido, 0.5 = mitad.
        """

    @abstractmethod
    def list_voices(self) -> list[str]:
        """Voces instaladas localmente y listas para usar."""
