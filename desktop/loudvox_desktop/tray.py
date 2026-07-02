"""Ícono en la bandeja del sistema (junto al reloj) con menú.

Es la interfaz principal para cerrar la aplicación y para acciones rápidas
con el mouse, pensada para usuarios que no usan la terminal.
"""

from __future__ import annotations

import threading


def _icon_image():
    """Botón play naranja, dibujado al vuelo (sin archivos de assets)."""
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, size - 2, size - 2], radius=12, fill=(255, 140, 0, 255))
    d.polygon([(24, 18), (24, 46), (48, 32)], fill=(255, 255, 255, 255))
    return img


def run_tray(app) -> None:
    """Bloquea en el bucle del ícono. 'Salir' detiene todo y retorna."""
    import pystray

    def bg(fn):
        return lambda: threading.Thread(target=fn, daemon=True).start()

    hk = app.cfg.hotkeys
    menu = pystray.Menu(
        pystray.MenuItem("📋 Leer portapapeles", bg(app.read_clipboard)),
        pystray.MenuItem("🎤 Dictar (empezar / terminar)", bg(app.toggle_dictation)),
        pystray.MenuItem("⏹ Detener lectura", lambda: app.stop()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"Leer selección: {hk.read_selection}", None, enabled=False),
        pystray.MenuItem(f"Dictar: {hk.dictate}", None, enabled=False),
        pystray.MenuItem(f"Detener: {hk.stop}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Salir", lambda icon, item: icon.stop()),
    )
    icon = pystray.Icon("loudvox", _icon_image(), "LoudVox — lector local", menu)
    icon.run()  # bloquea hasta "Salir"
