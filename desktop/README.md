# LoudVox Desktop

Cliente de escritorio: lee en voz alta el texto seleccionado en **cualquier
aplicación** (visores de PDF, Word, editores, mail…) con hotkeys globales,
y lee archivos PDF/txt/md completos. Windows y Linux. 100% offline.

## Instalación (Windows, PowerShell)

Requiere el motor ya instalado (`engine/`, ver su README).

```powershell
cd desktop
pip install .
```

## Uso diario

```powershell
loudvox-desktop
```

Ese único proceso levanta todo: el motor TTS, el servidor local para la
extensión de Brave (ya no hace falta `loudvox serve` aparte) y las hotkeys
globales:

| Hotkey (por defecto) | Acción |
|---|---|
| `Ctrl+Alt+R` | Leer el texto seleccionado (en cualquier app) |
| `Ctrl+Alt+F` | Leer el contenido del portapapeles |
| `Ctrl+Alt+S` | Detener |

A diferencia del navegador, en el escritorio **sí se permite `Ctrl+Alt+…`**.

**Personalizarlas**: editá el archivo de configuración (`loudvox config`
muestra la ruta) — sección `hotkeys`, mínimo 2 teclas, sin restricciones:

```json
"hotkeys": {
  "read_selection": "ctrl+alt+r",
  "read_from_here": "ctrl+alt+f",
  "stop": "ctrl+alt+s",
  "dictate": "ctrl+alt+d"
}
```

(`dictate` se activa en la Fase 4.)

## Leer archivos

```powershell
loudvox-desktop file documento.pdf
loudvox-desktop file notas.md
loudvox-desktop file libro.txt --desde "capítulo tres"
loudvox-desktop file libro.pdf --desde-clip
```

`--desde` busca la frase (sin distinguir mayúsculas) y lee desde ahí, para
retomar donde dejaste.

**"Leer desde aquí" en un PDF**: copiá (Ctrl+C) una frase del punto donde
querés empezar en tu visor de PDF y ejecutá `--desde-clip` — usa el
portapapeles como punto de partida y lee de ahí al final. (La hotkey de
selección `Ctrl+Alt+R` también funciona dentro del visor para fragmentos.)

## Cómo funciona "leer selección"

Al presionar la hotkey se simula `Ctrl+C`, se toma el texto y **se restaura
tu portapapeles anterior**. Por eso funciona en cualquier aplicación que
permita copiar. El texto se trocea en fragmentos cortos y se sintetiza con
precarga: el audio arranca en ~0.2 s (con la voz ya cargada) y no se corta
entre fragmentos.

## Notas por plataforma

- **Windows**: audio por `winsound` (biblioteca estándar, sin dependencias).
- **Linux**: audio por `aplay` (paquete `alsa-utils`); portapapeles requiere
  `xclip` o `xsel`; hotkeys globales funcionan en X11.

## Tests

```powershell
pip install .[dev]
python -m pytest tests/
```
