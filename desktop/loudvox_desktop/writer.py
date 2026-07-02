"""Escribe texto en el campo con foco de cualquier aplicación.

Método: portapapeles + Ctrl+V simulado (fiable con acentos, eñes y textos
largos, a diferencia de simular tecla por tecla), restaurando el contenido
anterior del portapapeles.
"""

from __future__ import annotations

import time


def write_text(text: str, settle_ms: int = 150) -> None:
    import pyperclip
    from pynput.keyboard import Controller, Key

    if not text:
        return
    previous = ""
    try:
        previous = pyperclip.paste() or ""
    except Exception:
        pass

    pyperclip.copy(text)
    time.sleep(0.05)

    kb = Controller()
    # Soltar modificadores de la hotkey antes de simular Ctrl+V
    for key in (Key.ctrl, Key.alt, Key.shift, Key.cmd):
        try:
            kb.release(key)
        except Exception:
            pass
    time.sleep(0.05)
    with kb.pressed(Key.ctrl):
        kb.press("v")
        kb.release("v")
    time.sleep(settle_ms / 1000)

    try:
        pyperclip.copy(previous)
    except Exception:
        pass
