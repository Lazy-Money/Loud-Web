"""Obtiene el texto seleccionado en cualquier aplicación.

Técnica estándar (la misma de Verbify-TTS y similares): se simula Ctrl+C,
se lee el portapapeles y se restaura su contenido anterior. Funciona en
cualquier app que soporte copiar: navegadores, visores de PDF, Word, IDEs.
"""

from __future__ import annotations

import time


def get_clipboard() -> str:
    import pyperclip

    try:
        return pyperclip.paste() or ""
    except Exception:
        return ""


def get_selection(settle_ms: int = 250) -> str:
    """Copia la selección actual (Ctrl+C simulado) y la devuelve,
    restaurando el portapapeles original."""
    import pyperclip
    from pynput.keyboard import Controller, Key

    previous = get_clipboard()
    # Vaciar primero: así "leer algo" == "el portapapeles dejó de estar vacío"
    try:
        pyperclip.copy("")
    except Exception:
        pass

    kb = Controller()
    # Soltar los modificadores de la hotkey antes de simular Ctrl+C
    for key in (Key.ctrl, Key.alt, Key.shift, Key.cmd):
        try:
            kb.release(key)
        except Exception:
            pass
    time.sleep(0.05)

    with kb.pressed(Key.ctrl):
        kb.press("c")
        kb.release("c")
    time.sleep(settle_ms / 1000)

    text = get_clipboard()
    # Restaurar el portapapeles del usuario
    try:
        pyperclip.copy(previous)
    except Exception:
        pass
    return text.strip()
