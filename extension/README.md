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
6. Listo: aparece el ícono de LoudVox en la barra

## Uso

| Atajo | Acción |
|---|---|
| `Alt+R` | Leer el texto seleccionado |
| `Alt+A` | Leer desde la selección en adelante (con resaltado y auto-scroll) |
| `Alt+S` | Detener |

**Personalizar atajos**: `brave://extensions/shortcuts` → asigná la
combinación que quieras a cada acción (cualquier combinación de 2+ teclas
que Brave permita).

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

## Limitaciones conocidas (se resuelven en fases siguientes)

- **PDFs en el navegador**: el visor de PDF de Brave no permite content
  scripts. Los PDFs se leerán con el cliente de escritorio (Fase 3).
- **Google Docs**: usa renderizado especial (canvas); requiere integración
  propia, planificada más adelante.
- Páginas internas (`brave://…`) no son accesibles por diseño del navegador.
