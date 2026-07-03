"""Punto de entrada del ejecutable 'LoudVox Viewer.exe' (visor de documentos).
Recibe una ruta como argumento (doble clic → %1). Lo usa PyInstaller."""

import sys

from loudvox_desktop.viewer.app import main

if __name__ == "__main__":
    sys.exit(main())
