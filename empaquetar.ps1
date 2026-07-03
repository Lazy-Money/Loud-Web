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
if (-not (Test-Path (Join-Path $out "LoudVox.exe"))) {
    Write-Host "El empaquetado no genero LoudVox.exe. Revisa el log de arriba." -ForegroundColor Red
    Read-Host "`nEnter para cerrar" | Out-Null
    return
}
Write-Host "App compilada:" -ForegroundColor Green
Write-Host "  $out  (LoudVox.exe + 'LoudVox Viewer.exe')"

# 3. Preparar las voces que ya tenes, para que el instalador las incluya
#    (asi la compu de destino no necesita bajar nada la primera vez).
$vocesDst = Join-Path $repo "instalador\_voces"
New-Item -ItemType Directory -Force -Path $vocesDst | Out-Null
"Voces empaquetadas con LoudVox. Podes agregar mas desde Configuracion." |
    Out-File -Encoding utf8 (Join-Path $vocesDst "LEEME.txt")
$vocesSrc = Join-Path $env:LOCALAPPDATA "loudvox\voices"
if (Test-Path $vocesSrc) {
    Copy-Item "$vocesSrc\*" $vocesDst -Recurse -Force -ErrorAction SilentlyContinue
    $n = (Get-ChildItem $vocesDst -Filter *.onnx -ErrorAction SilentlyContinue).Count
    Write-Host "Voces incluidas en el instalador: $n" -ForegroundColor Gray
    if ($n -eq 0) {
        Write-Host "  (No hay voces instaladas en esta PC. El instalador se genera igual," -ForegroundColor Yellow
        Write-Host "   pero la compu de destino tendra que bajar una voz la primera vez.)" -ForegroundColor Yellow
    }
}

# 4. Compilar el instalador de un clic con Inno Setup (si esta disponible)
Write-Host ""
Write-Host "== Instalador de un clic (Inno Setup) ==" -ForegroundColor Cyan
$iscc = $null
foreach ($c in @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe")) {
    if (Test-Path $c) { $iscc = $c; break }
}
if (-not $iscc) { $iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source }

if ($iscc) {
    & $iscc "$repo\instalador\LoudVox.iss"
    $setup = Join-Path $repo "instalador\Output\LoudVox-Setup.exe"
    if (Test-Path $setup) {
        Write-Host ""
        Write-Host "LISTO. Instalador de un clic:" -ForegroundColor Green
        Write-Host "  $setup" -ForegroundColor Green
        Write-Host "Copia ESE archivo a la otra computadora y hace doble clic."
        Write-Host "No necesita PowerShell, ni Python, ni instalar nada previo."
    } else {
        Write-Host "Inno Setup corrio pero no aparecio el .exe. Revisa el log." -ForegroundColor Red
    }
} else {
    Write-Host "No encontre Inno Setup (ISCC.exe)." -ForegroundColor Yellow
    Write-Host "Instalalo una sola vez (gratis): https://jrsoftware.org/isdl.php"
    Write-Host "Despues volve a correr este script, o abri instalador\LoudVox.iss"
    Write-Host "en Inno Setup y pulsa Compile. Sale instalador\Output\LoudVox-Setup.exe"
}

Read-Host "`nEnter para cerrar" | Out-Null
