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


def run_tray(app, stop_event: threading.Event):
    """Arranca el ícono en su propio hilo y devuelve el icon.

    'Salir' dispara ``stop_event``. El hilo principal queda libre para
    esperar de forma interrumpible (así Ctrl+C también funciona).
    """
    import pystray

    def bg(fn):
        return lambda: threading.Thread(target=fn, daemon=True).start()

    def do_exit(icon, item):
        icon.visible = False
        icon.stop()
        stop_event.set()

    def open_settings():
        from .settings_ui import open_settings as open_ui

        open_ui(app)

    def open_viewer():
        # Proceso aparte: pywebview necesita su propio hilo principal.
        import subprocess
        import sys

        subprocess.Popen(
            [sys.executable, "-m", "loudvox_desktop.viewer"],
            start_new_session=True,
        )

    from .i18n import strings_for

    t = strings_for(app.cfg.resolved_ui_language())
    hk = app.cfg.hotkeys
    menu = pystray.Menu(
        pystray.MenuItem(t["tray_clip"], bg(app.read_clipboard)),
        pystray.MenuItem(t["tray_dictate"], bg(app.toggle_dictation)),
        pystray.MenuItem(t["tray_stop"], lambda: app.stop()),
        pystray.MenuItem(t["tray_viewer"], lambda: open_viewer()),
        pystray.MenuItem(t["tray_settings"], lambda: open_settings()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"{t['hk_read']}: {hk.read_selection}", None, enabled=False),
        pystray.MenuItem(f"{t['hk_dictate']}: {hk.dictate}", None, enabled=False),
        pystray.MenuItem(f"{t['hk_stop']}: {hk.stop}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(t["tray_exit"], do_exit),
    )
    icon = pystray.Icon("loudvox", _icon_image(), "LoudVox", menu)
    icon.run_detached()  # bucle del ícono en su propio hilo
    return icon
