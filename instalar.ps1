# ============================================================
#  Instalador de LoudVox para Windows (PowerShell)
#  Uso:  clic derecho sobre este archivo -> Ejecutar con PowerShell
#        (o en una terminal:  .\instalar.ps1)
# ============================================================

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot

function Titulo($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }

Titulo "LoudVox - Instalador"

# --- 1. Python -------------------------------------------------------------
try {
    $pyv = (python --version) 2>&1
    Write-Host "Python detectado: $pyv"
} catch {
    Write-Host "No se encontro Python. Instalalo desde https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "IMPORTANTE: marcar 'Add Python to PATH' en el instalador." -ForegroundColor Yellow
    exit 1
}

# --- 2. Instalar el motor y el cliente de escritorio ------------------------
Titulo "Instalando el motor de voz (puede tardar unos minutos)"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet "$repo\engine"
Titulo "Instalando el cliente de escritorio"
python -m pip install --quiet "$repo\desktop"

# --- 3. Voces de lectura -----------------------------------------------------
Titulo "Voces de lectura"
Write-Host "Espanol se instala siempre (~200 MB). Idiomas adicionales:"
$langs = @("es")
foreach ($extra in @(
    @{code="en"; name="Ingles (~130 MB)"},
    @{code="it"; name="Italiano (~90 MB)"},
    @{code="de"; name="Aleman (~90 MB)"}
)) {
    $r = Read-Host ("  Instalar " + $extra.name + "? [s/N]")
    if ($r -match "^[sSyY]") { $langs += $extra.code }
}
foreach ($l in $langs) {
    Write-Host "Descargando voces: $l"
    loudvox download $l
}

# --- 4. Dictado por voz (opcional) ------------------------------------------
Titulo "Dictado por voz (hablar y que escriba)"
Write-Host "Requiere descargar un modelo de reconocimiento (una sola vez):"
Write-Host "  1) base   (~150 MB)  - liviano, para PC modestas"
Write-Host "  2) small  (~500 MB)  - recomendado, buena precision en espanol"
Write-Host "  3) no instalar ahora (se puede activar despues)"
$op = Read-Host "Opcion [1/2/3]"
$sttModel = $null
if ($op -eq "1") { $sttModel = "base" }
if ($op -eq "2") { $sttModel = "small" }
if ($sttModel) {
    $gpu = Read-Host "Tenes placa NVIDIA con CUDA y queres usarla para el dictado? [s/N]"
    $device = "cpu"
    if ($gpu -match "^[sSyY]") { $device = "cuda" }
    # Escribir la config del usuario
    python -c @"
from loudvox.config import load, save
cfg = load()
cfg.stt_model = '$sttModel'
cfg.stt_device = '$device'
cfg.stt_preload = True
print('Config de dictado:', save(cfg))
"@
    Write-Host "Descargando el modelo de dictado ($sttModel)..."
    python -c @"
import os
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
from faster_whisper import WhisperModel
WhisperModel('$sttModel', device='cpu', compute_type='int8')
print('Modelo de dictado listo.')
"@
}

# --- 5. Accesos directos ------------------------------------------------------
Titulo "Accesos directos"
$pythonw = (Get-Command pythonw).Source
$shell = New-Object -ComObject WScript.Shell

function Crear-Acceso($ruta, $args, $nombre) {
    $lnk = $shell.CreateShortcut($ruta)
    $lnk.TargetPath = $pythonw
    $lnk.Arguments = $args
    $lnk.Description = "LoudVox - lector y dictado local"
    $lnk.Save()
    Write-Host "  creado: $nombre"
}

$menuDir = [Environment]::GetFolderPath('Programs')
Crear-Acceso "$menuDir\LoudVox.lnk" "-m loudvox_desktop.cli" "Menu Inicio"

$auto = Read-Host "Iniciar LoudVox automaticamente con Windows? [S/n]"
if ($auto -notmatch "^[nN]") {
    $startup = [Environment]::GetFolderPath('Startup')
    Crear-Acceso "$startup\LoudVox.lnk" "-m loudvox_desktop.cli" "Inicio automatico"
}

# --- 6. Fin -------------------------------------------------------------------
Titulo "Listo!"
Write-Host "
 - LoudVox quedo instalado. Inicialo desde el Menu Inicio (LoudVox)
   o reiniciando Windows si elegiste inicio automatico.
 - Vas a ver el icono naranja junto al reloj: clic derecho para
   Configuracion, dictar, detener o salir.
 - La extension de Brave se carga desde brave://extensions
   (Modo desarrollador -> Cargar sin empaquetar -> carpeta 'extension').
 - Registro de la app (si corre sin consola): %LOCALAPPDATA%\loudvox\loudvox.log
"
