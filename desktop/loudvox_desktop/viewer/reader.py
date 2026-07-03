"""Lectura en voz alta por párrafos, con aviso de progreso para la UI.

Diseño: la síntesis y la reproducción ocurren EN PYTHON (reutilizando
``Player``, ya probado en Windows/Linux con stop instantáneo), no en el
WebView. Motivos: (1) evita el problema de CORS del fetch desde la
ventana hacia el motor local; (2) no depende de los códecs de audio del
WebView (WebKitGTK en Linux es caprichoso); (3) hereda el corte
inmediato y la precarga del ``Player`` existente.

La UI solo manda la lista de párrafos y recibe callbacks de progreso
(``on_paragraph(i)``) para resaltar y hacer scroll.
"""

from __future__ import annotations

import threading

from loudvox.config import Config
from loudvox.normalizer import Normalizer
from loudvox.tts import get_backend

from ..chunker import chunk_text
from ..player import Player


class ParagraphReader:
    """Lee una lista de párrafos, avisando cuál está sonando.

    Los párrafos largos se trocean en frases (baja latencia) pero el
    resaltado sigue siendo por párrafo: se mapea cada fragmento a su
    índice de párrafo.
    """

    def __init__(self, cfg: Config, on_paragraph=None, on_end=None,
                 backend=None, player=None):
        self.cfg = cfg
        self._on_paragraph = on_paragraph or (lambda i: None)
        self._on_end = on_end or (lambda: None)
        self._backend = backend or get_backend(
            cfg.engine, cfg.resolved_voices_dir(), use_gpu=cfg.use_gpu
        )
        self._normalizer = Normalizer.for_language(cfg.language)
        self.player = player or Player(self._synthesize)
        self._lock = threading.Lock()
        self._session = 0
        self._last_paragraph = -1

    def reload_config(self, cfg: Config) -> None:
        """Aplica cambios de config (voz/idioma) sin recrear el lector."""
        self.cfg = cfg
        self._normalizer = Normalizer.for_language(cfg.language)
        self._backend = get_backend(
            cfg.engine, cfg.resolved_voices_dir(), use_gpu=cfg.use_gpu
        )

    def _synthesize(self, text: str) -> bytes:
        voice = self.cfg.resolved_voice()
        params = self.cfg.params_for(voice)
        wav = self._backend.synthesize(
            self._normalizer.normalize(text),
            voice,
            speed=params["speed"],
            volume=params["volume"],
            speaker=params["speaker"],
        )
        if params["pitch"]:
            from loudvox.audio import apply_pitch

            wav = apply_pitch(wav, params["pitch"])
        return wav

    def read(self, paragraphs: list[str], start_index: int = 0) -> None:
        """Lee desde ``start_index`` hasta el final. Cancela lo anterior."""
        with self._lock:
            self._session += 1
            session = self._session
        chunks: list[str] = []
        para_of_chunk: list[int] = []
        for i in range(start_index, len(paragraphs)):
            for piece in chunk_text(paragraphs[i]):
                chunks.append(piece)
                para_of_chunk.append(i)
        if not chunks:
            self._on_end()
            return

        def on_chunk(chunk_idx: int, _text: str) -> None:
            if session != self._session:
                return
            para = para_of_chunk[chunk_idx]
            if para != self._last_paragraph:
                self._last_paragraph = para
                self._on_paragraph(para)
            # último fragmento: avisar fin cuando termine de sonar lo hace
            # el hilo consumidor al vaciar la cola (ver Player.wait en stop)
            if chunk_idx == len(chunks) - 1:
                threading.Thread(
                    target=self._notify_end_after, args=(session,), daemon=True
                ).start()

        self._last_paragraph = -1
        self.player.play_text_chunks(chunks, on_chunk=on_chunk)

    def _notify_end_after(self, session: int) -> None:
        self.player.wait(timeout=None)
        if session == self._session:
            self._on_end()

    def stop(self) -> None:
        with self._lock:
            self._session += 1
        self.player.stop()
