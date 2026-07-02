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
        dll_dir: str = "",
    ):
        self.model_size = model_size
        self.language = language
        self.device = device
        # automático: lo más liviano por dispositivo
        self.compute = compute or ("int8_float16" if device == "cuda" else "int8")
        self.dll_dir = dll_dir
        self._model = None
        self._lock = threading.Lock()

# DLLs que ctranslate2 4.4 (CUDA 12 + cuDNN 8) carga sí o sí en GPU.
# Si falta alguna, tocar la GPU produce un aborto NATIVO incapturable:
# hay que verificar ANTES y caer a CPU.
_REQUIRED_CUDA_DLLS = ("cublas64_12.dll", "cudnn64_8.dll", "cudnn_ops_infer64_8.dll")


class _CudaDlls:
    """Localiza las DLLs de CUDA y las expone al cargador de Windows."""

    def __init__(self, model_path: str, dll_dir: str):
        self.model_path = model_path
        self.dll_dir = dll_dir

    def _candidate_dirs(self) -> list[str]:
        import os

        dirs: list[str] = []
        if self.dll_dir and os.path.isdir(self.dll_dir):
            dirs.append(self.dll_dir)
        # Cerca del modelo (Purfview: _models\... y _xxl_data\torch\lib son
        # subárboles hermanos: subir hasta 2 niveles y buscar recursivo)
        if os.path.isdir(self.model_path):
            from pathlib import Path

            d = os.path.abspath(self.model_path)
            ancestors = []
            for _ in range(3):
                ancestors.append(d)
                d = os.path.dirname(d)
            for root in ancestors:
                try:
                    hit = next(Path(root).rglob("cublas64*.dll"), None)
                except OSError:
                    hit = None
                if hit:
                    dirs.append(str(hit.parent))
                    break
        # Paquetes pip de NVIDIA
        try:
            import nvidia

            base = os.path.dirname(nvidia.__file__)
            for sub in os.listdir(base):
                for leaf in ("bin", "lib"):
                    p = os.path.join(base, sub, leaf)
                    if os.path.isdir(p):
                        dirs.append(p)
        except ImportError:
            pass
        # PATH del sistema (CUDA Toolkit instalado a mano)
        dirs.extend(p for p in os.environ.get("PATH", "").split(os.pathsep) if p)
        return dirs

    def preflight(self) -> tuple[bool, str]:
        """(ok, detalle). Si ok, además registra las carpetas halladas."""
        import os

        dirs = self._candidate_dirs()
        found: dict[str, str] = {}
        for dll in _REQUIRED_CUDA_DLLS:
            for d in dirs:
                if os.path.exists(os.path.join(d, dll)):
                    found[dll] = d
                    break
        missing = [d for d in _REQUIRED_CUDA_DLLS if d not in found]
        if missing:
            return False, f"faltan {', '.join(missing)}"
        # Registrar por las dos vías: add_dll_directory (Python) y PATH
        # (los LoadLibrary internos de cuDNN no siempre miran la primera).
        for d in dict.fromkeys(found.values()):
            try:
                os.add_dll_directory(d)
            except OSError:
                pass
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
        return True, f"DLLs en {', '.join(dict.fromkeys(found.values()))}"

    def _load(self):
        if self._model is None:
            import os
            import sys

            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            from faster_whisper import WhisperModel

            if self.device == "cuda" and sys.platform == "win32":
                # Verificación PREVIA: si falta una DLL, ctranslate2 aborta el
                # proceso entero (incapturable). Mejor detectarlo antes.
                ok, detail = _CudaDlls(self.model_size, self.dll_dir).preflight()
                if ok:
                    print(f"[loudvox] GPU lista ({detail})")
                else:
                    print(
                        f"[loudvox] GPU desactivada para el dictado: {detail}. "
                        "Se usa CPU. (Las DLLs deben ser CUDA 12 + cuDNN 8, "
                        "las mismas que trae Purfview/Subtitle Edit.)"
                    )
                    self.device = "cpu"
                    self.compute = "int8"
            try:
                self._model = WhisperModel(
                    self.model_size, device=self.device, compute_type=self.compute
                )
            except Exception as exc:
                if self.device != "cuda":
                    raise
                print(f"[loudvox] GPU no disponible ({exc}); usando CPU.")
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
