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
Write-Host "Elegi que idiomas instalar (se pueden agregar despues desde Configuracion):"
$langs = @()
foreach ($lang in @(
    @{code="es"; name="Espanol - Espana y Mexico (~250 MB)"},
    @{code="en"; name="Ingles - EE.UU. y Reino Unido (~130 MB)"},
    @{code="it"; name="Italiano (~90 MB)"},
    @{code="de"; name="Aleman (~90 MB)"}
)) {
    $r = Read-Host ("  Instalar " + $lang.name + "? [s/N]")
    if ($r -match "^[sSyY]") { $langs += $lang.code }
}
if ($langs.Count -eq 0) {
    Write-Host "No elegiste ninguno: se instala Ingles como minimo para que la app funcione." -ForegroundColor Yellow
    $langs = @("en")
}
foreach ($l in $langs) {
    Write-Host "Descargando voces: $l"
    loudvox download $l
}
# Idioma inicial de la app = el primero elegido
python -c @"
from loudvox.config import load, save
cfg = load()
cfg.language = '$($langs[0])'
save(cfg)
print('Idioma inicial:', cfg.language)
"@

# --- 4. Dictado por voz (opcional) ------------------------------------------
Titulo "Dictado por voz (hablar y que escriba)"
Write-Host "Opciones de modelo de reconocimiento:"
Write-Host "  1) base   (~150 MB, se descarga)  - liviano, para PC modestas"
Write-Host "  2) small  (~500 MB, se descarga)  - recomendado, buena precision"
Write-Host "  3) usar un modelo faster-whisper que YA TENGO en el disco"
Write-Host "     (p. ej. el de Subtitle Edit / Purfview; sin descargas)"
Write-Host "  4) no instalar el dictado ahora (se puede activar despues)"
$op = Read-Host "Opcion [1/2/3/4]"
$sttModel = $null
$needsDownload = $false
if ($op -eq "1") { $sttModel = "base";  $needsDownload = $true }
if ($op -eq "2") { $sttModel = "small"; $needsDownload = $true }
if ($op -eq "3") {
    $ruta = Read-Host "Ruta de la carpeta del modelo (contiene model.bin)"
    if (Test-Path (Join-Path $ruta "model.bin")) {
        $sttModel = $ruta.Replace('\', '\\')
    } else {
        Write-Host "No encontre model.bin en esa carpeta; el dictado queda sin configurar." -ForegroundColor Yellow
    }
}
if ($sttModel) {
    Write-Host "Procesador para el dictado:"
    Write-Host "  1) CPU (funciona en cualquier PC)"
    Write-Host "  2) GPU NVIDIA/CUDA (mas rapido; requiere drivers CUDA/cuDNN)"
    $d = Read-Host "Opcion [1/2]"
    $device = "cpu"
    if ($d -eq "2") { $device = "cuda" }
    # Escribir la config del usuario
    python -c @"
from loudvox.config import load, save
cfg = load()
cfg.stt_model = '$sttModel'
cfg.stt_device = '$device'
cfg.stt_preload = True
save(cfg)
print('Dictado configurado -> modelo:', cfg.stt_model, '| dispositivo:', cfg.stt_device)
"@
    if ($needsDownload) {
        Write-Host "Descargando el modelo de dictado ($sttModel)..."
        python -c @"
import os
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
from faster_whisper import WhisperModel
WhisperModel('$sttModel', device='cpu', compute_type='int8')
print('Modelo de dictado listo.')
"@
    }
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

# --- 6. Resumen ----------------------------------------------------------------
Titulo "Resumen de la instalacion"
python -c @"
from loudvox.config import load
cfg = load()
print(' Idioma inicial :', cfg.language)
print(' Voz            :', cfg.resolved_voice())
print(' Dictado        :', cfg.stt_model if cfg.stt_preload else '(no configurado)')
print(' Dispositivo STT:', cfg.stt_device)
print(' Config en      : se muestra con  loudvox config')
"@

# --- 7. Fin -------------------------------------------------------------------
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
