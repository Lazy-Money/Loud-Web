"""Hotkeys globales del sistema (Windows y Linux/X11) vía pynput.

Convierte el formato de configuración "ctrl+alt+r" al formato de pynput
"<ctrl>+<alt>+r". Combinaciones libres, mínimo 2 teclas (config.validate_hotkey).
"""

from __future__ import annotations

_MODIFIERS = {
    "ctrl": "<ctrl>",
    "control": "<ctrl>",
    "alt": "<alt>",
    "shift": "<shift>",
    "win": "<cmd>",
    "cmd": "<cmd>",
    "super": "<cmd>",
}
_SPECIAL = {
    "space": "<space>",
    "espacio": "<space>",
    "enter": "<enter>",
    "tab": "<tab>",
    "esc": "<esc>",
    "escape": "<esc>",
    "up": "<up>",
    "down": "<down>",
    "left": "<left>",
    "right": "<right>",
    "insert": "<insert>",
    "delete": "<delete>",
    "home": "<home>",
    "end": "<end>",
    **{f"f{i}": f"<f{i}>" for i in range(1, 13)},
}


def to_pynput(combo: str) -> str:
    parts = []
    for raw in combo.lower().split("+"):
        key = raw.strip()
        if key in _MODIFIERS:
            parts.append(_MODIFIERS[key])
        elif key in _SPECIAL:
            parts.append(_SPECIAL[key])
        elif len(key) == 1:
            parts.append(key)
        else:
            raise ValueError(f"Tecla desconocida en hotkey: {key!r} (de {combo!r})")
    return "+".join(parts)


def listen(bindings: dict[str, callable]):
    """Registra {combo_config: función} y devuelve el listener (ya iniciado).

    Las funciones se ejecutan en el hilo del listener: deben ser rápidas o
    delegar a otro hilo.
    """
    from pynput import keyboard

    mapping = {to_pynput(combo): fn for combo, fn in bindings.items()}
    listener = keyboard.GlobalHotKeys(mapping)
    listener.start()
    return listener
