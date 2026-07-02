# ============================================================
#  Loud Web Installer  (Windows / PowerShell)
#  Uso: clic derecho -> Ejecutar con PowerShell   (o .\instalar.ps1)
#  Script transparente a proposito: leelo antes de ejecutarlo.
# ============================================================

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot

# --- Seleccion de idioma del instalador --------------------------------------
Write-Host ""
Write-Host "== Loud Web Installer ==" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1] Deutsch   [2] English   [3] Espanol   [4] Italiano"
$nl = Read-Host "N"
$LANG = @{ "1" = "de"; "2" = "en"; "3" = "es"; "4" = "it" }[$nl]
if (-not $LANG) { $LANG = "en" }

# --- Textos -------------------------------------------------------------------
$T = @{
  es = @{
    need_py     = "No se encontro Python. Instalalo desde https://www.python.org/downloads/ (marcando 'Add Python to PATH')."
    py_found    = "Python detectado:"
    inst_engine = "Instalando el motor de voz (puede tardar unos minutos)..."
    inst_desk   = "Instalando el cliente de escritorio..."
    voices_hdr  = "Voces de lectura"
    voices_ask  = "Elegi que idiomas de VOCES instalar (podes agregar mas despues desde Configuracion):"
    ask_install = "Instalar {0}? [s/N]"
    none_chosen = "No elegiste ninguno: se instala Ingles como minimo."
    downloading = "Descargando voces:"
    stt_hdr     = "Dictado por voz (hablar y que escriba)"
    stt_menu    = "  1) base  (~150 MB, descarga) - liviano`n  2) small (~500 MB, descarga) - recomendado`n  3) usar un modelo faster-whisper que YA TENGO en el disco`n  4) no instalar el dictado ahora"
    option      = "Opcion"
    stt_path    = "Ruta de la carpeta del modelo (contiene model.bin)"
    bad_path    = "No encontre model.bin ahi; el dictado queda sin configurar."
    dev_menu    = "  1) CPU (cualquier PC)`n  2) GPU NVIDIA/CUDA (mas rapido)"
    gpu_libs    = "La GPU necesita las librerias CUDA de NVIDIA (~600 MB via pip). Instalarlas ahora? [s/N]"
    dl_model    = "Descargando el modelo de dictado..."
    shortcuts   = "Accesos directos"
    autostart   = "Iniciar LoudVox automaticamente con Windows? [S/n]"
    made        = "  creado:"
    summary     = "Resumen"
    done        = "Listo! LoudVox instalado. Inicialo desde el Menu Inicio; vas a ver el icono naranja junto al reloj. Extension de Brave: brave://extensions -> Modo desarrollador -> Cargar sin empaquetar -> carpeta 'extension'."
    err         = "ERROR - la instalacion no se completo:"
    press_exit  = "Presiona Enter para cerrar"
    langs       = @{ es = "Espanol - Espana y Mexico (~250 MB)"; en = "Ingles (~130 MB)"; it = "Italiano (~90 MB)"; de = "Aleman (~90 MB)" }
  }
  en = @{
    need_py     = "Python not found. Install it from https://www.python.org/downloads/ (check 'Add Python to PATH')."
    py_found    = "Python detected:"
    inst_engine = "Installing the voice engine (this can take a few minutes)..."
    inst_desk   = "Installing the desktop client..."
    voices_hdr  = "Reading voices"
    voices_ask  = "Choose which VOICE languages to install (more can be added later in Settings):"
    ask_install = "Install {0}? [y/N]"
    none_chosen = "None chosen: installing English as the minimum."
    downloading = "Downloading voices:"
    stt_hdr     = "Voice dictation (speak and it types)"
    stt_menu    = "  1) base  (~150 MB, download) - light`n  2) small (~500 MB, download) - recommended`n  3) use a faster-whisper model I ALREADY HAVE on disk`n  4) skip dictation for now"
    option      = "Option"
    stt_path    = "Path to the model folder (contains model.bin)"
    bad_path    = "model.bin not found there; dictation left unconfigured."
    dev_menu    = "  1) CPU (any PC)`n  2) NVIDIA/CUDA GPU (faster)"
    gpu_libs    = "GPU needs NVIDIA's CUDA libraries (~600 MB via pip). Install them now? [y/N]"
    dl_model    = "Downloading the dictation model..."
    shortcuts   = "Shortcuts"
    autostart   = "Start LoudVox automatically with Windows? [Y/n]"
    made        = "  created:"
    summary     = "Summary"
    done        = "Done! LoudVox installed. Launch it from the Start Menu; look for the orange icon by the clock. Brave extension: brave://extensions -> Developer mode -> Load unpacked -> 'extension' folder."
    err         = "ERROR - installation did not finish:"
    press_exit  = "Press Enter to close"
    langs       = @{ es = "Spanish - Spain & Mexico (~250 MB)"; en = "English (~130 MB)"; it = "Italian (~90 MB)"; de = "German (~90 MB)" }
  }
  it = @{
    need_py     = "Python non trovato. Installalo da https://www.python.org/downloads/ (spunta 'Add Python to PATH')."
    py_found    = "Python rilevato:"
    inst_engine = "Installazione del motore vocale (puo richiedere qualche minuto)..."
    inst_desk   = "Installazione del client desktop..."
    voices_hdr  = "Voci di lettura"
    voices_ask  = "Scegli quali lingue di VOCI installare (altre si aggiungono dopo dalle Impostazioni):"
    ask_install = "Installare {0}? [s/N]"
    none_chosen = "Nessuna scelta: installo l'inglese come minimo."
    downloading = "Scaricamento voci:"
    stt_hdr     = "Dettatura vocale (parli e scrive)"
    stt_menu    = "  1) base  (~150 MB, download) - leggero`n  2) small (~500 MB, download) - consigliato`n  3) usare un modello faster-whisper GIA PRESENTE su disco`n  4) non installare ora la dettatura"
    option      = "Opzione"
    stt_path    = "Percorso della cartella del modello (contiene model.bin)"
    bad_path    = "model.bin non trovato; dettatura non configurata."
    dev_menu    = "  1) CPU (qualsiasi PC)`n  2) GPU NVIDIA/CUDA (piu veloce)"
    gpu_libs    = "La GPU richiede le librerie CUDA di NVIDIA (~600 MB via pip). Installarle ora? [s/N]"
    dl_model    = "Scaricamento del modello di dettatura..."
    shortcuts   = "Collegamenti"
    autostart   = "Avviare LoudVox automaticamente con Windows? [S/n]"
    made        = "  creato:"
    summary     = "Riepilogo"
    done        = "Fatto! LoudVox installato. Avvialo dal Menu Start; icona arancione accanto all'orologio. Estensione Brave: brave://extensions -> Modalita sviluppatore -> Carica non pacchettizzata -> cartella 'extension'."
    err         = "ERRORE - installazione non completata:"
    press_exit  = "Premi Invio per chiudere"
    langs       = @{ es = "Spagnolo - Spagna e Messico (~250 MB)"; en = "Inglese (~130 MB)"; it = "Italiano (~90 MB)"; de = "Tedesco (~90 MB)" }
  }
  de = @{
    need_py     = "Python nicht gefunden. Installiere es von https://www.python.org/downloads/ ('Add Python to PATH' ankreuzen)."
    py_found    = "Python erkannt:"
    inst_engine = "Sprach-Engine wird installiert (kann einige Minuten dauern)..."
    inst_desk   = "Desktop-Client wird installiert..."
    voices_hdr  = "Vorlesestimmen"
    voices_ask  = "Welche STIMMEN-Sprachen installieren? (weitere spaeter in den Einstellungen):"
    ask_install = "{0} installieren? [j/N]"
    none_chosen = "Keine Auswahl: Englisch wird als Minimum installiert."
    downloading = "Stimmen werden geladen:"
    stt_hdr     = "Diktat (sprechen und es schreibt)"
    stt_menu    = "  1) base  (~150 MB, Download) - leicht`n  2) small (~500 MB, Download) - empfohlen`n  3) vorhandenes faster-whisper-Modell von der Festplatte verwenden`n  4) Diktat jetzt nicht installieren"
    option      = "Option"
    stt_path    = "Pfad zum Modellordner (enthaelt model.bin)"
    bad_path    = "model.bin dort nicht gefunden; Diktat bleibt unkonfiguriert."
    dev_menu    = "  1) CPU (jeder PC)`n  2) NVIDIA/CUDA-GPU (schneller)"
    gpu_libs    = "Die GPU benoetigt NVIDIAs CUDA-Bibliotheken (~600 MB via pip). Jetzt installieren? [j/N]"
    dl_model    = "Diktatmodell wird geladen..."
    shortcuts   = "Verknuepfungen"
    autostart   = "LoudVox automatisch mit Windows starten? [J/n]"
    made        = "  erstellt:"
    summary     = "Zusammenfassung"
    done        = "Fertig! LoudVox installiert. Start ueber das Startmenue; orangefarbenes Symbol neben der Uhr. Brave-Erweiterung: brave://extensions -> Entwicklermodus -> Entpackt laden -> Ordner 'extension'."
    err         = "FEHLER - Installation nicht abgeschlossen:"
    press_exit  = "Enter druecken zum Schliessen"
    langs       = @{ es = "Spanisch - Spanien & Mexiko (~250 MB)"; en = "Englisch (~130 MB)"; it = "Italienisch (~90 MB)"; de = "Deutsch (~90 MB)" }
  }
}
$M = $T[$LANG]
$yes = "[sSyYjJ]"

function Titulo($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }

try {
    # --- 1. Python ------------------------------------------------------------
    try {
        $pyv = (python --version) 2>&1
        Write-Host "$($M.py_found) $pyv"
    } catch {
        throw $M.need_py
    }

    # --- 2. Motor + escritorio -------------------------------------------------
    Titulo $M.inst_engine
    python -m pip install --quiet --upgrade pip
    python -m pip install --quiet "$repo\engine"
    Titulo $M.inst_desk
    python -m pip install --quiet "$repo\desktop"

    # --- 3. Voces ----------------------------------------------------------------
    Titulo $M.voices_hdr
    Write-Host $M.voices_ask
    $langs = @()
    foreach ($code in @("de", "en", "es", "it")) {
        $r = Read-Host ("  " + ($M.ask_install -f $M.langs[$code]))
        if ($r -match "^$yes") { $langs += $code }
    }
    if ($langs.Count -eq 0) {
        Write-Host $M.none_chosen -ForegroundColor Yellow
        $langs = @("en")
    }
    foreach ($l in $langs) {
        Write-Host "$($M.downloading) $l"
        loudvox download $l
    }
    # Idioma inicial de la app: el del instalador si se instalaron sus voces,
    # si no, el primero elegido
    $appLang = if ($langs -contains $LANG) { $LANG } else { $langs[0] }
    python -c "from loudvox.config import load, save; cfg = load(); cfg.language = '$appLang'; save(cfg)"

    # --- 4. Dictado ---------------------------------------------------------------
    Titulo $M.stt_hdr
    Write-Host $M.stt_menu
    $op = Read-Host "$($M.option) [1/2/3/4]"
    $sttModel = $null
    $needsDownload = $false
    if ($op -eq "1") { $sttModel = "base";  $needsDownload = $true }
    if ($op -eq "2") { $sttModel = "small"; $needsDownload = $true }
    if ($op -eq "3") {
        $ruta = Read-Host $M.stt_path
        if (Test-Path (Join-Path $ruta "model.bin")) {
            $sttModel = $ruta.Replace('\', '\\')
        } else {
            Write-Host $M.bad_path -ForegroundColor Yellow
        }
    }
    if ($sttModel) {
        Write-Host $M.dev_menu
        $d = Read-Host "$($M.option) [1/2]"
        $device = "cpu"
        if ($d -eq "2") {
            $device = "cuda"
            $g = Read-Host $M.gpu_libs
            if ($g -match "^$yes") {
                python -m pip install --quiet nvidia-cublas-cu12 nvidia-cudnn-cu12
            }
        }
        python -c "from loudvox.config import load, save; cfg = load(); cfg.stt_model = '$sttModel'; cfg.stt_device = '$device'; cfg.stt_preload = True; save(cfg)"
        if ($needsDownload) {
            Write-Host $M.dl_model
            python -c "import os; os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING','1'); from faster_whisper import WhisperModel; WhisperModel('$sttModel', device='cpu', compute_type='int8')"
        }
    }

    # --- 5. Accesos directos ---------------------------------------------------
    Titulo $M.shortcuts
    $pythonw = (Get-Command pythonw).Source
    $shell = New-Object -ComObject WScript.Shell
    function Crear-Acceso($ruta, $args2, $nombre) {
        $lnk = $shell.CreateShortcut($ruta)
        $lnk.TargetPath = $pythonw
        $lnk.Arguments = $args2
        $lnk.Description = "LoudVox"
        $lnk.Save()
        Write-Host "$($M.made) $nombre"
    }
    $menuDir = [Environment]::GetFolderPath('Programs')
    Crear-Acceso "$menuDir\LoudVox.lnk" "-m loudvox_desktop.cli" "LoudVox (Menu)"
    $auto = Read-Host $M.autostart
    if ($auto -notmatch "^[nN]") {
        $startup = [Environment]::GetFolderPath('Startup')
        Crear-Acceso "$startup\LoudVox.lnk" "-m loudvox_desktop.cli" "Autostart"
    }

    # --- 6. Resumen ----------------------------------------------------------------
    Titulo $M.summary
    python -c "from loudvox.config import load; cfg = load(); print(' language :', cfg.language); print(' voice    :', cfg.resolved_voice()); print(' dictation:', cfg.stt_model if cfg.stt_preload else '-'); print(' device   :', cfg.stt_device)"

    Titulo "OK"
    Write-Host $M.done
}
catch {
    Write-Host ""
    Write-Host $M.err -ForegroundColor Red
    Write-Host $_ -ForegroundColor Red
    Write-Host $_.ScriptStackTrace
}
finally {
    Write-Host ""
    Read-Host $M.press_exit | Out-Null
}
