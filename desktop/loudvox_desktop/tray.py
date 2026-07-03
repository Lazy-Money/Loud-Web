"""Ícono en la bandeja del sistema (junto al reloj) con menú.

Es la interfaz principal para cerrar la aplicación y para acciones rápidas
con el mouse, pensada para usuarios que no usan la terminal.
"""

from __future__ import annotations

import threading

from .assets import icon_image, set_app_id


def run_tray(app, stop_event: threading.Event):
    """Arranca el ícono en su propio hilo y devuelve el icon.

    'Salir' dispara ``stop_event``. El hilo principal queda libre para
    esperar de forma interrumpible (así Ctrl+C también funciona).
    """
    import pystray

    # Que la barra de tareas muestre "LoudVox" y su icono, no "Python".
    set_app_id("LoudVox.Desktop")

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
        from pathlib import Path

        if getattr(sys, "frozen", False):
            # Empaquetado: lanzar el .exe hermano del visor.
            exe = Path(sys.executable).with_name("LoudVox Viewer.exe")
            cmd = [str(exe)]
        else:
            cmd = [sys.executable, "-m", "loudvox_desktop.viewer"]
        subprocess.Popen(cmd, start_new_session=True)

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
    icon = pystray.Icon("loudvox", icon_image("loudvox"), "LoudVox", menu)
    icon.run_detached()  # bucle del ícono en su propio hilo
    return icon
