"""CLI de LoudVox Desktop.

  loudvox-desktop                  # hotkeys globales + servidor local
  loudvox-desktop file doc.pdf     # leer un archivo (pdf/txt/md)
  loudvox-desktop file notas.md --desde "capítulo 3"
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="loudvox-desktop", description=__doc__)
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="hotkeys globales + servidor (por defecto)")
    p_run.add_argument("--no-server", action="store_true", help="sin servidor HTTP")
    p_run.add_argument("--port", type=int, default=5089)

    p_file = sub.add_parser("file", help="leer un archivo pdf/txt/md")
    p_file.add_argument("path")
    p_file.add_argument("--desde", default="", help="empezar desde esta frase")

    args = parser.parse_args(argv)

    from .app import DesktopApp

    try:
        app = DesktopApp()
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.command == "file":
        try:
            app.read_file(args.path, args.desde)
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
