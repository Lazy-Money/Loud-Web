; ============================================================
;  LoudVox - Instalador de un clic (Inno Setup)
;  Genera "LoudVox-Setup.exe": la persona final solo hace doble clic.
;  Sin PowerShell, sin Python, sin consola. Instalacion por usuario
;  (no pide permisos de administrador).
;
;  Como compilarlo (una sola vez, en TU Windows):
;    1) Instalar Inno Setup (gratis): https://jrsoftware.org/isdl.php
;    2) Antes, generar la app:  .\empaquetar.ps1   (crea dist\LoudVox\)
;    3) Abrir este archivo con Inno Setup y pulsar "Compile" (o correr
;       empaquetar.ps1, que ya lo compila si encuentra Inno Setup).
;  Sale:  instalador\Output\LoudVox-Setup.exe
; ============================================================

#define MyAppName "LoudVox"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "LoudVox"
#define MyAppExe "LoudVox.exe"
#define MyViewerExe "LoudVox Viewer.exe"

[Setup]
; AppId fijo: identifica la app para actualizaciones y desinstalacion.
AppId={{8B5E2A14-0C3D-4F76-9A2B-1E7D6C4F9013}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Instalacion por usuario: sin UAC, sin administrador (ideal para la abuela).
PrivilegesRequired=lowest
DefaultDirName={autopf}\LoudVox
DisableProgramGroupPage=yes
DisableDirPage=yes
OutputDir=Output
OutputBaseFilename=LoudVox-Setup
SetupIconFile=..\desktop\loudvox_desktop\assets\loudvox.ico
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
; La app trae su propio Python empaquetado: no requiere nada preinstalado.

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked
Name: "autostart"; Description: "Iniciar LoudVox automaticamente al encender la computadora"
Name: "assoc"; Description: "Abrir PDF, TXT, MD y DJVU con el visor de LoudVox"; Flags: unchecked

[Files]
; 1) La app (salida de PyInstaller: los dos .exe + _internal con las deps).
Source: "..\dist\LoudVox\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; 2) Voces (si empaquetar.ps1 las copio aca): quedan listas, sin bajar nada.
;    onlyifdoesntexist: no pisa voces que el usuario ya tenga.
Source: "_voces\*"; DestDir: "{localappdata}\loudvox\voices"; Flags: recursesubdirs createallsubdirs onlyifdoesntexist skipifsourcedoesntexist
; 3) Config por defecto en espanol (solo si el usuario no tiene una ya).
Source: "config.default.json"; DestDir: "{userappdata}\loudvox"; DestName: "config.json"; Flags: onlyifdoesntexist

[Icons]
Name: "{autoprograms}\LoudVox"; Filename: "{app}\{#MyAppExe}"
Name: "{autoprograms}\LoudVox Viewer"; Filename: "{app}\{#MyViewerExe}"
Name: "{autodesktop}\LoudVox"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Registry]
; Autostart (llave Run del usuario; se borra al desinstalar).
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; \
    ValueName: "LoudVox"; ValueData: """{app}\{#MyAppExe}"""; Tasks: autostart; Flags: uninsdeletevalue

; Asociacion de archivos (opcional): agrega LoudVox Viewer a "Abrir con".
; No roba la app por defecto; todo se borra al desinstalar.
Root: HKCU; Subkey: "Software\Classes\LoudVox.Viewer"; ValueType: string; ValueData: "LoudVox Viewer"; Tasks: assoc; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\LoudVox.Viewer\DefaultIcon"; ValueType: string; ValueData: "{app}\{#MyViewerExe},0"; Tasks: assoc
Root: HKCU; Subkey: "Software\Classes\LoudVox.Viewer\shell\open\command"; ValueType: string; ValueData: """{app}\{#MyViewerExe}"" ""%1"""; Tasks: assoc
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "LoudVox.Viewer"; ValueData: ""; Tasks: assoc; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.txt\OpenWithProgids"; ValueType: string; ValueName: "LoudVox.Viewer"; ValueData: ""; Tasks: assoc; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.md\OpenWithProgids"; ValueType: string; ValueName: "LoudVox.Viewer"; ValueData: ""; Tasks: assoc; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.djvu\OpenWithProgids"; ValueType: string; ValueName: "LoudVox.Viewer"; ValueData: ""; Tasks: assoc; Flags: uninsdeletevalue

[Run]
; Ofrecer arrancar la app al terminar (casilla marcada en el ultimo paso).
Filename: "{app}\{#MyAppExe}"; Description: "Iniciar LoudVox ahora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Limpieza opcional: no borramos voces ni config del usuario a proposito
; (por si reinstala). El desinstalador quita la app y las llaves creadas.
Type: filesandordirs; Name: "{app}"
