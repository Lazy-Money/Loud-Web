"""Reproductor con cola: sintetiza fragmentos y los reproduce en orden,
precargando el siguiente mientras suena el actual. Detención inmediata.

Backends de audio:
  - Windows: winsound (biblioteca estándar, sin dependencias)
  - Linux:   aplay (alsa-utils)
"""

from __future__ import annotations

import io
import queue
import subprocess
import sys
import threading
import wave


def wav_duration(wav: bytes) -> float:
    """Duración en segundos de un WAV en memoria."""
    with wave.open(io.BytesIO(wav)) as w:
        return w.getnframes() / w.getframerate()


class AudioSink:
    """Reproduce un WAV (bytes) de forma bloqueante pero interrumpible.

    En Windows, winsound sincrónico no puede cortarse desde otro hilo, así
    que se reproduce en modo asíncrono y se espera la duración del WAV con
    un Event: stop() lo dispara y el corte es inmediato.
    """

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._stopped = threading.Event()

    def play(self, wav: bytes) -> None:
        self._stopped.clear()
        if sys.platform == "win32":
            import os
            import tempfile
            import winsound

            # winsound NO permite SND_MEMORY + SND_ASYNC (RuntimeError), así
            # que se pasa por un archivo temporal: async desde archivo sí vale.
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            try:
                tmp.write(wav)
                tmp.close()
                winsound.PlaySound(
                    tmp.name,
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
                interrupted = self._stopped.wait(wav_duration(wav) + 0.05)
                if interrupted:
                    winsound.PlaySound(None, winsound.SND_PURGE)
            finally:
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass  # si el sistema aún lo retiene, queda en %TEMP%
        else:
            self._proc = subprocess.Popen(
                ["aplay", "-q", "-"],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            try:
                self._proc.communicate(wav)
            except BrokenPipeError:
                pass
            finally:
                self._proc = None

    def stop(self) -> None:
        self._stopped.set()
        if sys.platform == "win32":
            import winsound

            winsound.PlaySound(None, winsound.SND_PURGE)
        elif self._proc is not None:
            try:
                self._proc.terminate()
            except ProcessLookupError:
                pass


class Player:
    """Cola de lectura: synth (con prefetch) -> audio, en hilos propios."""

    def __init__(self, synthesize, sink: AudioSink | None = None, prefetch: int = 2):
        """``synthesize(text) -> bytes WAV``; inyectable para tests."""
        self._synthesize = synthesize
        self._sink = sink or AudioSink()
        self._prefetch = prefetch
        self._session = 0
        self._lock = threading.Lock()
        self._threads: list[threading.Thread] = []

    @property
    def busy(self) -> bool:
        return any(t.is_alive() for t in self._threads)

    def play_text_chunks(self, chunks: list[str], on_chunk=None) -> None:
        """Lee la lista de fragmentos. Cancela cualquier lectura anterior."""
        with self._lock:
            self._session += 1
            session = self._session
        self._sink.stop()

        audio_q: queue.Queue = queue.Queue(maxsize=self._prefetch)

        def producer():
            for i, chunk in enumerate(chunks):
                if session != self._session:
                    return
                try:
                    wav = self._synthesize(chunk)
                except Exception as exc:  # seguir con el resto
                    print(f"[loudvox] error sintetizando fragmento {i}: {exc}")
                    continue
                audio_q.put((i, wav))
            audio_q.put(None)  # fin

        def consumer():
            while True:
                item = audio_q.get()
                if item is None or session != self._session:
                    return
                i, wav = item
                if on_chunk:
                    on_chunk(i, chunks[i])
                self._sink.play(wav)

        t1 = threading.Thread(target=producer, daemon=True)
        t2 = threading.Thread(target=consumer, daemon=True)
        self._threads = [t1, t2]
        t1.start()
        t2.start()

    def stop(self) -> None:
        with self._lock:
            self._session += 1
        self._sink.stop()

    def wait(self, timeout: float | None = None) -> None:
        for t in self._threads:
            t.join(timeout)
