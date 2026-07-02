"""LoudVox Desktop: proceso único que levanta todo.

- Motor TTS en el mismo proceso (sin latencia HTTP para el escritorio)
- Servidor local en 127.0.0.1:5089 (para la extensión del navegador)
- Hotkeys globales (config.json, personalizables):
    read_selection  -> lee el texto seleccionado en CUALQUIER aplicación
    read_from_here  -> lee el contenido actual del portapapeles
    stop            -> detiene la lectura

También puede leer archivos directamente:  loudvox-desktop file doc.pdf
"""

from __future__ import annotations

import threading

from loudvox.config import Config, load
from loudvox.normalizer import Normalizer
from loudvox.tts import get_backend

from .chunker import chunk_text
from .player import Player


class DesktopApp:
    def __init__(self, cfg: Config | None = None):
        self.cfg = cfg or load()
        self.backend = get_backend(
            self.cfg.engine, self.cfg.resolved_voices_dir(), use_gpu=self.cfg.use_gpu
        )
        self._normalizer = Normalizer.for_language(self.cfg.language)
        self.player = Player(self._synthesize)
        self._dictation = None  # se arma en el primer uso (carga diferida)

    def _beep(self, event: str) -> None:
        """Señal sonora del dictado: aguda al empezar, grave al terminar."""
        import sys

        tones = {"start": 880, "stop": 550, "done": 660, "empty": 330, "error": 220}
        if sys.platform == "win32":
            import winsound

            winsound.Beep(tones.get(event, 440), 120)
        else:
            print(f"[loudvox] dictado: {event}")

    def toggle_dictation(self) -> None:
        if self._dictation is None:
            from .stt import DictationController, Recorder, Transcriber
            from .writer import write_text

            transcriber = Transcriber(
                model_size=self.cfg.stt_model, language=self.cfg.language
            )
            self._dictation = DictationController(
                recorder=Recorder(),
                transcribe=transcriber.transcribe,
                write=write_text,
                feedback=self._beep,
            )
            print(
                f"[loudvox] dictado listo (modelo {self.cfg.stt_model}; la primera "
                "transcripción descarga el modelo y puede tardar)"
            )
        self._dictation.toggle()
        state = "grabando… (misma tecla para terminar)" if self._dictation.recording else "procesando…"
        print(f"[loudvox] dictado: {state}")

    def _synthesize(self, text: str) -> bytes:
        text = self._normalizer.normalize(text)
        voice = self.cfg.resolved_voice()
        params = self.cfg.params_for(voice)
        return self.backend.synthesize(
            text,
            voice,
            speed=params["speed"],
            volume=params["volume"],
            speaker=params["speaker"],
        )

    # --- acciones de hotkeys ---------------------------------------------

    def read_selection(self) -> None:
        from .clipboard import get_selection

        text = get_selection()
        if not text:
            print("[loudvox] no hay texto seleccionado")
            return
        self._read(text)

    def read_clipboard(self) -> None:
        from .clipboard import get_clipboard

        text = get_clipboard().strip()
        if not text:
            print("[loudvox] portapapeles vacío")
            return
        self._read(text)

    def read_file(self, path: str, start_phrase: str = "") -> None:
        from .files import extract_text, find_start

        text = extract_text(path)
        if start_phrase:
            text = find_start(text, start_phrase)
        self._read(text)

    def _read(self, text: str) -> None:
        chunks = chunk_text(text)
        if not chunks:
            return
        total = len(chunks)
        print(f"[loudvox] leyendo {total} fragmento(s)…")
        self.player.play_text_chunks(
            chunks, on_chunk=lambda i, c: print(f"  ▶ {i + 1}/{total}: {c[:60]}…")
        )

    def stop(self) -> None:
        print("[loudvox] detenido")
        self.player.stop()

    # --- ciclo principal ---------------------------------------------------

    def _warmup(self) -> None:
        """Carga el modelo en memoria para que la primera hotkey responda al
        instante (la carga inicial tarda unos segundos)."""
        try:
            self._synthesize("hola")
            print("[loudvox] voz cargada y lista")
        except FileNotFoundError as exc:
            print(f"[loudvox] AVISO: {exc}")

    def run(self, with_server: bool = True, port: int = 5089, tray: bool = True) -> None:
        from .hotkeys import listen

        threading.Thread(target=self._warmup, daemon=True).start()
        if with_server:
            from loudvox.server import serve

            threading.Thread(
                target=serve, kwargs={"port": port, "cfg": self.cfg}, daemon=True
            ).start()

        hk = self.cfg.hotkeys
        listener = listen(
            {
                hk.read_selection: lambda: threading.Thread(
                    target=self.read_selection, daemon=True
                ).start(),
                hk.read_from_here: lambda: threading.Thread(
                    target=self.read_clipboard, daemon=True
                ).start(),
                hk.stop: self.stop,
                hk.dictate: lambda: threading.Thread(
                    target=self.toggle_dictation, daemon=True
                ).start(),
            }
        )
        print("LoudVox Desktop activo. Hotkeys:")
        print(f"  {hk.read_selection:>18}  leer selección (en cualquier app)")
        print(f"  {hk.read_from_here:>18}  leer portapapeles")
        print(f"  {hk.dictate:>18}  dictar (empezar / terminar)")
        print(f"  {hk.stop:>18}  detener")

        if tray:
            try:
                from .tray import run_tray

                print("Ícono en la bandeja del sistema (junto al reloj): "
                      "clic derecho → Salir para cerrar.")
                run_tray(self)  # bloquea hasta "Salir"
                self.player.stop()
                listener.stop()
                print("Hasta luego.")
                return
            except Exception as exc:
                print(f"[loudvox] bandeja no disponible ({exc}); modo consola.")

        print("Ctrl+C en esta terminal para salir.")
        # En Windows, un join() sin timeout no puede interrumpirse con Ctrl+C:
        # se espera en intervalos cortos para que la señal llegue.
        try:
            while listener.is_alive():
                listener.join(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.player.stop()
            listener.stop()
            print("\nHasta luego.")
