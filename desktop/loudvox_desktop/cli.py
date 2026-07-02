"""CLI de LoudVox Desktop.

  loudvox-desktop                  # hotkeys globales + servidor local
  loudvox-desktop file doc.pdf     # leer un archivo (pdf/txt/md)
  loudvox-desktop file notas.md --desde "capítulo 3"
"""

from __future__ import annotations

import argparse
import sys


def _setup_headless_io() -> None:
    """Con pythonw (sin consola) sys.stdout/err son None y print() rompería.
    Redirigimos a un log en la carpeta de datos para poder diagnosticar."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    from loudvox.config import data_dir

    log_path = data_dir() / "loudvox.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = log
    if sys.stderr is None:
        sys.stderr = log


def main(argv: list[str] | None = None) -> int:
    _setup_headless_io()
    parser = argparse.ArgumentParser(prog="loudvox-desktop", description=__doc__)
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="hotkeys globales + servidor (por defecto)")
    p_run.add_argument("--no-server", action="store_true", help="sin servidor HTTP")
    p_run.add_argument("--port", type=int, default=5089)

    p_stt = sub.add_parser("stt", help="probar la transcripción con un WAV")
    p_stt.add_argument("wav", help="archivo WAV a transcribir")

    p_file = sub.add_parser("file", help="leer un archivo pdf/txt/md")
    p_file.add_argument("path")
    p_file.add_argument("--desde", default="", help="empezar desde esta frase")
    p_file.add_argument(
        "--desde-clip",
        action="store_true",
        help="empezar desde la frase que esté copiada en el portapapeles "
        "(copiá una frase del documento y ejecutá este comando)",
    )

    args = parser.parse_args(argv)

    from .app import DesktopApp

    try:
        app = DesktopApp()
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.command == "stt":
        import wave as wave_mod

        import numpy as np

        from loudvox_desktop.stt import Transcriber

        with wave_mod.open(args.wav) as w:
            rate = w.getframerate()
            audio = np.frombuffer(
                w.readframes(w.getnframes()), dtype=np.int16
            ).astype(np.float32) / 32768.0
        if rate != 16000:  # remuestreo lineal simple
            idx = np.linspace(0, len(audio) - 1, int(len(audio) * 16000 / rate))
            audio = np.interp(idx, np.arange(len(audio)), audio).astype(np.float32)
        t = Transcriber(model_size=app.cfg.stt_model, language=app.cfg.language)
        print("Transcribiendo (la primera vez descarga el modelo)…")
        print(f"» {t.transcribe(audio)}")
        return 0

    if args.command == "file":
        start = args.desde
        if getattr(args, "desde_clip", False) and not start:
            from .clipboard import get_clipboard

            # Las primeras ~12 palabras alcanzan para ubicar el punto de inicio
            start = " ".join(get_clipboard().split()[:12])
            if not start:
                print("Error: el portapapeles está vacío.", file=sys.stderr)
                return 1
            print(f"[loudvox] empezando desde: “{start}…”")
        try:
            app.read_file(args.path, start)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        try:
            app.player.wait()
        except KeyboardInterrupt:
            app.stop()
        return 0

    # run (por defecto)
    no_server = getattr(args, "no_server", False)
    port = getattr(args, "port", 5089)
    app.run(with_server=not no_server, port=port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
