"""Dictado por voz: grabación de micrófono + transcripción local (Whisper).

Todo ocurre en tu máquina: faster-whisper corre el modelo en CPU. La única
descarga es la del modelo, una vez, la primera vez que dictás.
"""

from __future__ import annotations

import threading


class Recorder:
    """Graba el micrófono (16 kHz mono, el formato que espera Whisper)."""

    def __init__(self, samplerate: int = 16000):
        self.samplerate = samplerate
        self._chunks: list = []
        self._stream = None

    def start(self) -> None:
        import sounddevice as sd

        self._chunks = []

        def callback(indata, frames, time_info, status):
            self._chunks.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            dtype="float32",
            callback=callback,
        )
        self._stream.start()

    def stop(self):
        """Devuelve el audio grabado como np.ndarray float32 mono."""
        import numpy as np

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._chunks:
            return np.zeros(0, dtype="float32")
        return np.concatenate(self._chunks).flatten()


class Transcriber:
    """faster-whisper local, carga diferida (la primera vez tarda)."""

    def __init__(self, model_size: str = "small", language: str = "es"):
        self.model_size = model_size
        self.language = language
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            # int8: el modo más liviano en CPU, precisión casi idéntica
            self._model = WhisperModel(
                self.model_size, device="cpu", compute_type="int8"
            )
        return self._model

    def transcribe(self, audio) -> str:
        if len(audio) < 1600:  # menos de 0.1 s: nada que transcribir
            return ""
        with self._lock:
            model = self._load()
            segments, _info = model.transcribe(
                audio,
                language=self.language,
                vad_filter=True,  # ignora silencios y respiraciones
            )
            return " ".join(s.text.strip() for s in segments).strip()


class DictationController:
    """Máquina de estados del dictado: hotkey alterna grabar/transcribir.

    Todas las dependencias son inyectables para poder testear sin micrófono
    ni modelo: ``recorder``, ``transcribe(audio)->str``, ``write(text)`` y
    ``feedback(event)`` (eventos: start, stop, done, empty, error).
    """

    def __init__(self, recorder, transcribe, write, feedback=None):
        self._recorder = recorder
        self._transcribe = transcribe
        self._write = write
        self._feedback = feedback or (lambda event: None)
        self._recording = False
        self._lock = threading.Lock()

    @property
    def recording(self) -> bool:
        return self._recording

    def toggle(self) -> None:
        with self._lock:
            if not self._recording:
                try:
                    self._recorder.start()
                except Exception as exc:
                    self._feedback("error")
                    print(f"[loudvox] no se pudo abrir el micrófono: {exc}")
                    return
                self._recording = True
                self._feedback("start")
            else:
                audio = self._recorder.stop()
                self._recording = False
                self._feedback("stop")
                # Transcribir fuera del lock (puede tardar segundos)
                threading.Thread(
                    target=self._finish, args=(audio,), daemon=True
                ).start()

    def _finish(self, audio) -> None:
        try:
            text = self._transcribe(audio)
        except Exception as exc:
            self._feedback("error")
            print(f"[loudvox] error transcribiendo: {exc}")
            return
        if not text:
            self._feedback("empty")
            return
        self._write(text)
        self._feedback("done")
