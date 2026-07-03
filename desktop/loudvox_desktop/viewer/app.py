"""Ventana del visor de documentos (pywebview) y entrada de línea de comandos.

``loudvox-viewer [archivo]`` abre la ventana nativa con la UI de ``ui/``.
Con argumento, abre ese documento; sin argumento, muestra los recientes.
Este es el comando que invoca el doble clic cuando LoudVox está asociado
a .pdf/.txt/.md/.djvu (ver instalar.ps1).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bridge import ViewerApi

UI_DIR = Path(__file__).resolve().parent / "ui"


def _bind_drop(window) -> None:
    """Entrega a la UI la ruta real de los archivos soltados en la ventana.

    El DOM no expone rutas de archivos locales; pywebview sí, mediante su
    manejador de eventos del lado Python (``pywebviewFullPath``).
    """
    from webview.dom import DOMEventHandler

    def on_drop(e):
        for f in e.get("dataTransfer", {}).get("files", []):
            path = f.get("pywebviewFullPath")
            if path:
                window.evaluate_js(f"lv.openDropped({json.dumps(path)})")

    window.dom.document.events.drop += DOMEventHandler(
        on_drop, prevent_default=True, stop_propagation=True
    )


def run(initial_path: str | None = None) -> None:
    """Crea la ventana y bloquea hasta que se cierre (hilo principal)."""
    import webview

    from loudvox.config import load as load_config

    from ..assets import icon_path, set_app_id
    from ..i18n import strings_for

    # Barra de tareas: identidad propia del visor (no "Python").
    set_app_id("LoudVox.Viewer")

    api = ViewerApi(initial_path=initial_path)
    title = strings_for(load_config().resolved_ui_language())["vw_title"]
    window = webview.create_window(
        title,
        url=str(UI_DIR / "viewer.html"),
        js_api=api,
        width=1100,
        height=800,
        min_size=(720, 480),
    )
    api.set_window(window)
    # El icono de la ventana/barra: pywebview lo toma del parámetro de start()
    # en GTK/Qt; en Windows (EdgeChromium) lo hereda del .exe empaquetado.
    ico = icon_path("loudvox_viewer")
    start_kwargs = {"icon": str(ico)} if ico.exists() else {}
    try:
        webview.start(_bind_drop, window, **start_kwargs)
    except TypeError:
        # Backends que no aceptan icon= en start(): seguir sin icono.
        webview.start(_bind_drop, window)
    finally:
        api.stop()  # que no quede audio sonando al cerrar la ventana


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="loudvox-viewer",
        description="Visor de documentos de LoudVox (PDF, TXT, MD, DJVU) "
        "con lectura en voz alta.",
    )
    parser.add_argument("file", nargs="?", help="documento a abrir")
    args = parser.parse_args(argv)
    run(initial_path=args.file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
