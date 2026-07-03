# -*- mode: python ; coding: utf-8 -*-
"""Empaquetado de LoudVox con PyInstaller (onedir, dos ejecutables).

Produce una carpeta ``dist/LoudVox/`` con:
  - LoudVox.exe          (cliente principal: bandeja, hotkeys, dictado)
  - LoudVox Viewer.exe   (visor de documentos)
compartiendo un unico ``_internal/`` (dependencias) via MERGE.

Uso normal (Windows):   pyinstaller desktop/packaging/loudvox.spec
Validacion (Linux):     LOUDVOX_TARGETS=viewer pyinstaller ... (solo el visor,
                         que no depende de pystray/pynput/sounddevice).

No cruza plataformas: el .exe de Windows se compila en Windows.
"""

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parent.parent            # raiz del repo
DESKTOP = ROOT / "desktop"
ENGINE = ROOT / "engine"
ASSETS = DESKTOP / "loudvox_desktop" / "assets"

targets = [t.strip() for t in os.environ.get("LOUDVOX_TARGETS", "tray,viewer").split(",") if t.strip()]

# --- dependencias que necesitan recoleccion explicita (datos + binarios) ------
datas, binaries, hiddenimports = [], [], []
for pkg in ("piper", "espeakng_loader", "onnxruntime", "ctranslate2",
            "faster_whisper", "webview", "sounddevice", "pystray", "pynput",
            "kokoro_onnx",
            # Windows: pywebview usa el backend EdgeChromium via pythonnet.
            "clr", "pythonnet", "cffi"):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass  # opcional o ausente en esta plataforma

# backends por plataforma que los hooks a veces omiten (import condicional)
hiddenimports += [
    "pystray._win32", "pynput.keyboard._win32", "pynput.mouse._win32",
    "pystray._xorg", "pynput.keyboard._xorg", "pynput.mouse._xorg",
    "webview.platforms.edgechromium", "webview.platforms.winforms",
    "webview.platforms.gtk",
    "clr",
]

# --- datos PROPIOS, en las rutas que el codigo espera al descongelarse --------
#  normalizer.py:  BUNDLED_DIR = loudvox/../dictionaries  -> _internal/dictionaries
#  viewer/app.py:  UI_DIR = viewer/ui                     -> _internal/loudvox_desktop/viewer/ui
#  assets/__init__:HERE  = assets                         -> _internal/loudvox_desktop/assets
datas += [
    (str(ENGINE / "dictionaries"), "dictionaries"),
    (str(DESKTOP / "loudvox_desktop" / "viewer" / "ui"), "loudvox_desktop/viewer/ui"),
    (str(ASSETS), "loudvox_desktop/assets"),
]

pathex = [str(DESKTOP), str(ENGINE)]


def make_analysis(entry):
    return Analysis(
        [str(DESKTOP / "packaging" / entry)],
        pathex=pathex,
        binaries=binaries,
        datas=datas,
        hiddenimports=hiddenimports,
        hookspath=[],
        runtime_hooks=[],
        excludes=["tkinter"],   # settings_ui usa tkinter; se importa perezoso
        noarchive=False,
    )


analyses = {}
if "tray" in targets:
    analyses["tray"] = make_analysis("entry_tray.py")
if "viewer" in targets:
    analyses["viewer"] = make_analysis("entry_viewer.py")
if not analyses:
    raise SystemExit("LOUDVOX_TARGETS no seleccciono ningun objetivo")

# Compartir dependencias entre los dos exes (evita duplicar _internal)
if len(analyses) > 1:
    MERGE(
        (analyses["tray"], "entry_tray", "LoudVox"),
        (analyses["viewer"], "entry_viewer", "LoudVox Viewer"),
    )

collect_items = []


def add_exe(key, name, icon):
    a = analyses[key]
    pyz = PYZ(a.pure, a.zipped_data)
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name=name,
        console=False,               # app de ventana/bandeja, sin consola
        icon=str(ASSETS / icon),
    )
    collect_items.extend([exe, a.binaries, a.datas])


if "tray" in analyses:
    add_exe("tray", "LoudVox", "loudvox.ico")
if "viewer" in analyses:
    add_exe("viewer", "LoudVox Viewer", "loudvox_viewer.ico")

coll = COLLECT(*collect_items, strip=False, upx=False, name="LoudVox")
