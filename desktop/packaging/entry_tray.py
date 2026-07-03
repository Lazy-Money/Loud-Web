"""Punto de entrada del ejecutable LoudVox.exe (cliente principal: bandeja,
servidor local, hotkeys, dictado). Lo usa PyInstaller."""

import sys

from loudvox_desktop.cli import main

if __name__ == "__main__":
    sys.exit(main([]))
