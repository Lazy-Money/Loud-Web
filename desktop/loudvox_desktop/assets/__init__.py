"""Iconos empaquetados de LoudVox y utilidades de identidad en Windows.

Los .ico/.png se generan con ``generate_icons.py`` y se commitean, para que
tanto el instalador como PyInstaller los usen sin ejecutar PIL.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def icon_path(name: str = "loudvox") -> Path:
    """Ruta al .ico (para accesos directos, PyInstaller, ventana)."""
    return HERE / f"{name}.ico"


def icon_png(name: str = "loudvox") -> Path:
    return HERE / f"{name}.png"


def icon_image(name: str = "loudvox"):
    """Imagen PIL para la bandeja (pystray). Si falta el archivo, la dibuja."""
    from PIL import Image

    p = icon_png(name)
    if p.exists():
        return Image.open(p).convert("RGBA")
    # Respaldo: play naranja dibujado al vuelo (mismo diseño).
    from PIL import ImageDraw

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, 62, 62], radius=12, fill=(255, 140, 0, 255))
    d.polygon([(24, 18), (24, 46), (48, 32)], fill=(255, 255, 255, 255))
    return img


def set_app_id(app_id: str) -> None:
    """Fija el AppUserModelID para que la barra de tareas de Windows agrupe
    la app con SU nombre e icono, en vez de mostrarla como 'Python'.

    No-op fuera de Windows o si la llamada falla (no es crítica).
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass
