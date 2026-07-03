# ============================================================
#  LoudVox - Empaquetar como .exe  (Windows / PowerShell)
#  Genera dist\LoudVox\ con LoudVox.exe y "LoudVox Viewer.exe".
#  Alternativa transparente al codigo fuente + instalar.ps1.
# ============================================================
#
#  Requisitos: Windows con Python, y haber instalado antes el motor y el
#  cliente (instalar.ps1 los deja listos, con pywebview -> pythonnet).
#  Este script NO descarga voces: las voces y el modelo de dictado se
#  bajan la primera vez que uses la app, igual que con la instalacion normal.
#
#  El .exe SOLO se puede generar en Windows (PyInstaller no cruza
#  plataformas). Para la ventana del visor, Windows 10/11 ya trae el
#  runtime "Edge WebView2"; si faltara, se instala solo desde Microsoft.

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot

Write-Host "== LoudVox: empaquetado .exe ==" -ForegroundColor Cyan

# 1. Asegurar motor + cliente + PyInstaller en este mismo Python
Write-Host "Instalando/actualizando dependencias..." -ForegroundColor Gray
python -m pip install --quiet --upgrade "$repo\engine" "$repo\desktop"
python -m pip install --quiet "pyinstaller==6.21.0"

# 2. Compilar los dos ejecutables (comparten _internal via MERGE)
$env:LOUDVOX_TARGETS = "tray,viewer"
python -m PyInstaller "$repo\desktop\packaging\loudvox.spec" `
    --distpath "$repo\dist" --workpath "$repo\build" --noconfirm

$out = Join-Path $repo "dist\LoudVox"
Write-Host ""
if (Test-Path (Join-Path $out "LoudVox.exe")) {
    Write-Host "Listo. Carpeta portable:" -ForegroundColor Green
    Write-Host "  $out"
    Write-Host "  - LoudVox.exe          (bandeja + hotkeys + dictado)"
    Write-Host "  - LoudVox Viewer.exe   (visor de documentos)"
    Write-Host ""
    Write-Host "Podes mover esa carpeta a donde quieras y crear accesos a los .exe."
    Write-Host "Para asociar .pdf/.txt/.md/.djvu al visor: ver docs\VISOR.md"
} else {
    Write-Host "El empaquetado no genero LoudVox.exe. Revisa el log de arriba." -ForegroundColor Red
}

Read-Host "`nEnter para cerrar" | Out-Null
