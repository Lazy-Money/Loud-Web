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
    """faster-whisper local, carga diferida (la primera vez tarda).

    ``model_size`` acepta un nombre ("small", "large-v2"…) o una ruta a un
    modelo faster-whisper ya descargado en tu disco.
    """

    def __init__(
        self,
        model_size: str = "small",
        language: str = "es",
        device: str = "cpu",
        compute: str = "",
    ):
        self.model_size = model_size
        self.language = language
        self.device = device
        # automático: lo más liviano por dispositivo
        self.compute = compute or ("int8_float16" if device == "cuda" else "int8")
        self._model = None
        self._lock = threading.Lock()

    def _add_nvidia_dll_dirs(self) -> None:
        """Registra carpetas con DLLs de CUDA (solo Windows), en este orden:

        1. La carpeta del propio modelo (y su padre): las builds de
           Purfview/Subtitle Edit traen cublas/cudnn AL LADO del modelo,
           así que se reutilizan sin descargar nada.
        2. Los paquetes pip de NVIDIA si están instalados
           (nvidia-cublas-cu12 / nvidia-cudnn-cu12).
        """
        import os
        import sys

        if sys.platform != "win32":
            return

        def add(d):
            if os.path.isdir(d):
                try:
                    os.add_dll_directory(d)
                except OSError:
                    pass

        # 1. Junto al modelo (ruta local tipo Purfview). Su estructura es
        #    Purfview-Whisper-Faster\           <- acá viven cublas/cudnn
        #      _models\faster-whisper-large-v2\ <- acá está model.bin
        #    así que hay que subir hasta 2 niveles desde el modelo.
        if os.path.isdir(self.model_size):
            d = os.path.abspath(self.model_size)
            for _ in range(3):
                add(d)
                d = os.path.dirname(d)

        # 2. Paquetes pip de NVIDIA
        try:
            import nvidia  # noqa: F401
        except ImportError:
            return
        base = os.path.dirname(nvidia.__file__)
        for sub in os.listdir(base):
            for leaf in ("bin", "lib"):
                add(os.path.join(base, sub, leaf))

    def _load(self):
        if self._model is None:
            import os

            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            from faster_whisper import WhisperModel

            if self.device == "cuda":
                self._add_nvidia_dll_dirs()
            try:
                self._model = WhisperModel(
                    self.model_size, device=self.device, compute_type=self.compute
                )
            except Exception as exc:
                if self.device != "cuda":
                    raise
                # GPU sin CUDA/cuDNN disponibles: caer a CPU en vez de romper.
                print(
                    f"[loudvox] GPU no disponible para el dictado ({exc}); "
                    "usando CPU. Para GPU: pip install nvidia-cublas-cu12 "
                    "nvidia-cudnn-cu12"
                )
                self.device = "cpu"
                self.compute = "int8"
                self._model = WhisperModel(
                    self.model_size, device="cpu", compute_type="int8"
                )
        return self._model

    def preload(self) -> None:
        with self._lock:
            self._load()

    def transcribe(self, audio) -> str:
        if len(audio) < 1600:  # menos de 0.1 s: nada que transcribir
            return ""
        with self._lock:
            model = self._load()
            try:
                segments, _info = model.transcribe(
                    audio,
                    language=self.language,
                    vad_filter=True,  # ignora silencios y respiraciones
                )
                return " ".join(s.text.strip() for s in segments).strip()
            except (RuntimeError, OSError) as exc:
                if self.device != "cuda":
                    raise
                # cublas/cudnn ausentes recién se detectan al transcribir:
                # recargar en CPU y reintentar una vez.
                print(f"[loudvox] GPU falló al transcribir ({exc}); reintento en CPU")
                self.device = "cpu"
                self.compute = "int8"
                self._model = None
                model = self._load()
                segments, _info = model.transcribe(
                    audio, language=self.language, vad_filter=True
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
