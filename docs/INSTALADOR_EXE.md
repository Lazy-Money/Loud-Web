# Instalador de un clic (`LoudVox-Setup.exe`)

Para instalar LoudVox en la computadora de otra persona **sin PowerShell, sin
Python y sin consola** — solo un doble clic — se genera un `LoudVox-Setup.exe`.

Vos lo generás **una vez en tu computadora** y después copiás ese único archivo
a la otra PC.

## En TU computadora (una vez)

1. **Instalá Inno Setup** (gratis, es la herramienta estándar para armar
   instaladores de Windows): <https://jrsoftware.org/isdl.php>. Se instala como
   cualquier programa; no hay que configurar nada.

2. **Tené LoudVox andando** en tu PC (con `instalar.ps1`), y **con al menos una
   voz instalada** (elegí español en el instalador, o bajala desde
   Configuración → “Bajar voces del idioma”). Esas voces se van a incluir en el
   instalador, así la otra computadora **no necesita bajar nada**.

3. **Corré, en la carpeta del repo:**
   ```powershell
   .\empaquetar.ps1
   ```
   El script hace todo solo:
   - compila la app en dos ejecutables (`LoudVox.exe` y `LoudVox Viewer.exe`),
   - copia las voces que ya tenés,
   - y, si encuentra Inno Setup, genera el instalador.

4. **Resultado:**
   ```
   instalador\Output\LoudVox-Setup.exe
   ```

## En la computadora de la otra persona

Copiale **solo** `LoudVox-Setup.exe` (pendrive, mail, lo que sea) y que haga
**doble clic**. El asistente:

- No pide permisos de administrador (instala solo para ese usuario).
- Crea los accesos “LoudVox” y “LoudVox Viewer” en el menú Inicio.
- Ofrece (con casillas) iniciar con Windows y abrir PDF/TXT/MD/DJVU con el visor.
- Deja la app en español y lista para usar, con la voz ya incluida.
- Crea un **desinstalador** normal (Panel de control → Programas), que borra
  todo lo que agregó.

No hace falta Python ni internet: la app trae su propio Python empaquetado, y la
ventana del visor usa el runtime **Edge WebView2** que Windows 10/11 ya incluye.

## Qué archivo es cada cosa

| Archivo | Para qué |
|---|---|
| `instalar.ps1` | Instalar desde el código fuente (transparente, para auditar). |
| `empaquetar.ps1` | Generar los `.exe` **y** el `LoudVox-Setup.exe`. |
| `instalador\LoudVox.iss` | La receta del instalador (Inno Setup). |
| `desktop\packaging\loudvox.spec` | La receta del empaquetado (PyInstaller). |
| `instalador\Output\LoudVox-Setup.exe` | **El instalador de un clic** (lo que copiás). |

## Nota honesta sobre la verificación

Todo esto **se compila en Windows** (PyInstaller e Inno Setup no funcionan desde
Linux). El `spec` de PyInstaller se validó compilando el visor en Linux (imports,
datos de voz e íconos quedan incluidos), y el script `.iss` sigue la sintaxis
estándar de Inno Setup, pero **el `LoudVox-Setup.exe` final y su comportamiento
en la PC de destino solo se confirman corriéndolo en Windows**. Cuando lo
generes y lo pruebes, contame qué ves y ajustamos.
