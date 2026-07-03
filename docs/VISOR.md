# Visor de documentos de LoudVox

Ventana de escritorio que abre **PDF, TXT, MD y DJVU** con **pestañas**,
**archivos recientes** y **lectura en voz alta integrada** (resaltado del
párrafo que suena + auto-scroll). Usa la misma voz, velocidad, volumen y tono
que configuraste en LoudVox (⚙️ Configuración).

100% local: no toca internet. La ventana es nativa (pywebview) y la síntesis
y el audio corren en Python con el mismo reproductor del resto de la app
(corte instantáneo, precarga del párrafo siguiente).

## Cómo abrirlo

- **Desde la bandeja**: clic derecho en el ícono naranja → **📖 Abrir visor…**
- **Desde el Menú Inicio** (Windows): acceso directo **LoudVox Viewer**
  (lo crea `instalar.ps1`).
- **Por comando**: `loudvox-viewer` (vacío, con recientes) o
  `loudvox-viewer ruta/al/archivo.pdf`.
- **Arrastrar y soltar** un archivo sobre la ventana también lo abre.

## Botones

| Botón | Qué hace |
|---|---|
| 📂 Abrir… | Diálogo para elegir un documento |
| ▶ Leer todo | Lee el documento desde el principio |
| ⏩ Desde aquí | Lee desde el párrafo de la selección (o desde el primero visible en pantalla si no hay selección) |
| 🔊 Selección | Lee solo el texto seleccionado |
| ⏹ Detener | Corta la lectura al instante |
| A− / A+ | Achica / agranda la letra (se recuerda) |

El párrafo que está sonando queda **resaltado** y la página lo sigue sola.
Las pestañas de arriba permiten tener varios documentos abiertos; la pantalla
inicial muestra los últimos 12 archivos (guardados en `recent.json`, en la
carpeta de configuración de LoudVox).

## DJVU: necesita djvulibre

Para leer DJVU hace falta la herramienta de sistema **djvulibre** (extrae la
capa de texto con `djvutxt`):

- **Windows**: instalador en <https://djvu.sourceforge.net/> (o
  `winget install DjVuLibre.DjVuLibre`), y que `djvutxt.exe` quede en el PATH.
- **Linux**: `sudo apt install djvulibre-bin` (Debian/Ubuntu) o equivalente.

Si el DJVU es un **escaneo sin capa de texto**, el visor lo dice claramente
(el OCR queda fuera de alcance). Si djvulibre no está instalado, el aviso
explica qué instalar.

## Asociar tipos de archivo (doble clic) — opcional y reversible

### Windows

`instalar.ps1` lo ofrece como paso opcional. Lo que hace: agrega
**LoudVox Viewer** al menú **"Abrir con"** de `.pdf .txt .md .djvu`, solo para
tu usuario (claves en `HKCU`, sin permisos de administrador). **No** cambia tu
aplicación por defecto: Windows 10/11 no permite cambiarla por script, y está
bien que la decisión sea tuya. Para que sea la predeterminada:

> clic derecho en un archivo → **Abrir con** → *Elegir otra aplicación* →
> **LoudVox Viewer** → marcar **"Siempre"**.

**Revertir** (borra exactamente lo que creó el instalador):

```powershell
Remove-Item -Recurse "HKCU:\Software\Classes\LoudVox.Viewer"
foreach ($ext in ".pdf", ".txt", ".md", ".djvu") {
  Remove-ItemProperty "HKCU:\Software\Classes\$ext\OpenWithProgids" -Name "LoudVox.Viewer" -ErrorAction SilentlyContinue
}
```

### Linux

Copiá el lanzador y (si querés) hacelo app por defecto:

```bash
cp desktop/linux/loudvox-viewer.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications 2>/dev/null

# opcional: por defecto para PDF y DJVU
xdg-mime default loudvox-viewer.desktop application/pdf image/vnd.djvu
```

**Revertir**: borrá el archivo y, si lo hiciste por defecto, volvé a tu app
anterior:

```bash
rm ~/.local/share/applications/loudvox-viewer.desktop
xdg-mime default org.gnome.Evince.desktop application/pdf   # ejemplo
```

## Empaquetar como .exe (Windows)

Además de la instalación desde el código con `instalar.ps1`, podés generar
ejecutables `.exe` con PyInstaller. Desde la raíz del repo, en Windows:

```powershell
.\empaquetar.ps1
```

Genera una carpeta **portable** `dist\LoudVox\` con:

- `LoudVox.exe` — cliente principal (bandeja, hotkeys, dictado).
- `LoudVox Viewer.exe` — el visor de documentos.

Ambos comparten un único `_internal\` (las dependencias), cada uno con su
ícono. Podés mover esa carpeta a donde quieras y crear accesos directos a los
`.exe`; para el doble clic en documentos, asociá los tipos como se explica
arriba (apuntando al `LoudVox Viewer.exe`).

Para un **instalador de un clic** (`LoudVox-Setup.exe`) que otra persona abre con
doble clic —sin PowerShell ni Python—, ver **[docs/INSTALADOR_EXE.md](INSTALADOR_EXE.md)**.

Notas honestas:

- **El `.exe` solo se compila en Windows.** PyInstaller no genera binarios de
  Windows desde Linux/Mac. El *spec* (`desktop/packaging/loudvox.spec`) se
  validó compilando el visor en Linux (imports, datos de espeak-ng, UI e
  íconos quedan incluidos), pero el ejecutable de Windows y su ventana solo se
  confirman en Windows.
- La ventana del visor usa el runtime **Edge WebView2**, que Windows 10/11 ya
  trae; si faltara, se instala solo desde Microsoft.
- `instalar.ps1` sigue disponible como alternativa transparente: instala el
  código fuente para quien quiera auditar exactamente qué corre.

## Para desarrolladores

- UI en `desktop/loudvox_desktop/viewer/ui/` (HTML/JS/CSS sin frameworks).
- Puente Python↔JS en `viewer/bridge.py` (js_api de pywebview).
- Extracción de párrafos en `loudvox_desktop/files.py` (pypdf / markdown /
  djvutxt) — un solo camino para los 4 formatos, testeable sin ventana.
- Lectura en `viewer/reader.py`: reutiliza `Player` (cola con precarga y stop
  inmediato) y avisa a la UI qué párrafo suena.
- Tests: `desktop/tests/test_viewer_*.py` incluye E2E headless con Playwright
  (la UI real hablando con el bridge real y el motor real).
