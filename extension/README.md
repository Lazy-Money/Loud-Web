# LoudVox — Extensión para Brave/Chrome

Lee en voz alta cualquier página web usando el motor local. Nada sale de tu
máquina: la extensión solo habla con `http://127.0.0.1:5089`.

## Instalación en Brave (Windows)

1. Asegurate de que el motor esté corriendo. En PowerShell:
   ```powershell
   loudvox serve
   ```
2. Abrí Brave y andá a `brave://extensions`
3. Activá **"Modo de desarrollador"** (interruptor arriba a la derecha)
4. Clic en **"Cargar extensión sin empaquetar"** (Load unpacked)
5. Seleccioná la carpeta `extension/` de este repo
6. **Para PDFs locales**: en la tarjeta de LoudVox tocá **Detalles** y activá
   **"Permitir el acceso a las URL de archivo"** — sin esto, el clic derecho
   sobre un PDF de tu disco no puede redirigir al lector
7. Listo: aparece el ícono de LoudVox en la barra

## Uso

**Con el mouse (clic derecho)** — pensado para no depender del teclado:

| Menú | Acción |
|---|---|
| 🔊 Leer selección | Lee el texto marcado |
| ⏩ Leer desde aquí en adelante | Lee desde la selección hasta el final |
| 🔊 Leer esta página completa | Lee todo el artículo desde el principio |
| ⏹ Detener lectura | Para |
| 📖 Abrir PDF con el lector LoudVox | (clic derecho sobre un enlace a PDF) |

**Con el teclado** (mismas acciones, para usuarios rápidos):

| Atajo | Acción |
|---|---|
| `Ctrl+Shift+L` | Leer el texto seleccionado |
| `Ctrl+Shift+Espacio` | Leer desde la selección en adelante (con resaltado y auto-scroll) |
| `Ctrl+Shift+X` | Detener |

## Lector de PDF integrado

El visor de PDF nativo de Brave está vedado para extensiones, así que LoudVox
trae su propio lector (basado en pdf.js de Mozilla, incluido en `vendor/`,
sin conexión a internet):

- **Abrir**: ícono de LoudVox → "📖 Abrir PDF con el lector" (elige el
  archivo o arrastralo a la ventana), o clic derecho sobre un enlace a PDF.
- Muestra el texto en página limpia, con letra grande ajustable (botones A− / A+).
- Ahí adentro funcionan el clic derecho, las hotkeys, el resaltado y el
  botón **▶ Leer todo**.

**Personalizar atajos**: `brave://extensions/shortcuts` → asigná la
combinación que quieras a cada acción (cualquier combinación de 2+ teclas
que Brave permita). Nota: Brave no acepta `Ctrl+Alt+...` para extensiones
(reservado por AltGr); sí acepta `Ctrl+Shift+...` y `Alt+Shift+...`.

**Si actualizás la extensión** (nueva versión de esta carpeta): en
`brave://extensions` tocá el botón de recarga (⟳) de LoudVox, y recargá
también las pestañas ya abiertas o usá los atajos directamente (la extensión
se auto-inyecta si hace falta).

**Popup** (clic en el ícono): estado del motor, idioma, voz, velocidad, y los
mismos tres botones para usar con el mouse.

## Cómo funciona

- **Leer selección**: sintetiza exactamente lo que marcaste.
- **Desde aquí**: detecta los párrafos del artículo desde tu selección hasta
  el final, salteando menús, publicidad, encabezados y pies de página.
  Resalta el párrafo que está sonando y hace scroll automático.
- El audio se pide al motor **párrafo por párrafo, con precarga del
  siguiente**: la lectura empieza rápido y no se corta entre párrafos.
- Las abreviaturas se expanden en el motor ("10 km" → "diez kilómetros").

## Limitaciones conocidas

- **PDFs escaneados** (imagen sin texto): el lector avisa; requerirá OCR
  (fase futura).
- **Google Docs**: usa renderizado especial (canvas); requiere integración
  propia, planificada más adelante.
- Páginas internas (`brave://…`) no son accesibles por diseño del navegador.
