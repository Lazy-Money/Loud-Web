# Prompt para Fable 5 — Construir el visor de documentos de LoudVox (Fase 7)

Copiá todo lo que está debajo de la línea en una sesión nueva de Claude Code
(Fable 5) apuntando al repo `Lazy-Money/Loud-Web`.

---

Sos un desarrollador senior trabajando en **LoudVox**, un lector de pantalla
(texto a voz) y dictado por voz, 100% local y auditable, para Windows y Linux.
Trabajás en el repositorio `Lazy-Money/Loud-Web`, rama
`claude/readvox-research-slumjx`. Desarrollá en esa rama, commiteá seguido con
mensajes claros (en inglés; código con comentarios en español, como el resto
del repo) y pushéá con `git push -u origin claude/readvox-research-slumjx`
(reintentá con backoff si falla por red). NO abras pull request salvo que se
te pida.

## Tu tarea: NO PARES HASTA TERMINARLA

Construir un **visor de documentos de escritorio** que abra **PDF, TXT, MD y
DJVU**, con **pestañas de archivos** y **lectura en voz alta integrada**
(estilo Sumatra + Readvox). Iterá —implementá, probá con archivos reales y el
motor real, corregí— hasta que funcione de punta a punta. No entregues a
medias ni delegues en herramientas de terceros: es código propio del proyecto.
Al final, reportá con honestidad qué verificaste vos y qué solo se puede
confirmar en una máquina con pantalla (el sandbox no tiene GUI).

## Contexto del repo (lo que YA existe y debés reutilizar)

- **Motor** (`engine/`, paquete `loudvox`): servidor HTTP local en
  `http://127.0.0.1:5089` (solo localhost). Endpoints:
  - `GET /health` → `{status, version}`
  - `GET /voices` → `{voices, catalog, language, engine, default_voice}`
    (el `catalog` trae `{id, engine, lang, region, name, gender, speaker, label}`)
  - `POST /normalize` `{text, language}` → `{text}` (expande abreviaturas)
  - `POST /speak` `{text, voice?, language?, speed?, volume?, pitch?, speaker?,
    normalize?}` → `audio/wav`
  - El motor se levanta con `loudvox serve` o dentro del cliente de escritorio.
- **Cliente de escritorio** (`desktop/`, paquete `loudvox_desktop`):
  - `app.py` (`DesktopApp`): levanta motor + servidor + hotkeys + bandeja.
  - `tray.py`: ícono de bandeja (pystray) con menú; agregá ahí una entrada
    "📖 Abrir visor…".
  - `settings_ui.py`: ventana de configuración (tkinter).
  - `player.py`: `AudioSink`/`Player` (reproducción con cola, stop instantáneo;
    winsound en Windows, aplay en Linux).
  - `files.py`: `extract_text(path)` ya soporta **pdf/txt/md** (usa pypdf y un
    limpiador de markdown). Reutilizalo y **extendelo a .djvu**.
  - `chunker.py`: `chunk_text()` trocea en frases para síntesis con baja latencia.
  - Config: `loudvox.config` (`config_dir()`, `data_dir()`, `Config` con
    `language`, `voice`, `speed`, `volume`, `pitch`, `engine`, `hotkeys`,
    `resolved_voice()`, `params_for(voice)`). Voces en `data_dir()/voices`.
- **Visor web ya hecho** (`extension/`): `viewer.html` + `viewer.js` +
  `viewer.css` renderizan PDF como texto limpio usando **pdf.js 6.1.200**
  (`extension/vendor/pdf.min.mjs`, `pdf.worker.min.mjs`). Tiene botones A−/A+,
  extracción de párrafos (`pageToParagraphs`), y lectura con resaltado.
  `content.js` tiene la lógica de leer selección / desde aquí / resaltar,
  y `offscreen.js` pide `/speak` al motor y reproduce con `Audio()`.
  **Portá y reutilizá esta lógica** — no la reescribas de cero.

## Requisitos funcionales del visor

1. **Ventana de escritorio nativa.** Usá **pywebview** (liviano, multiplataforma
   Win+Linux, envuelve HTML/JS/CSS en una ventana nativa). Fijá la versión en
   `desktop/pyproject.toml`. La UI (HTML/JS/CSS) vive en
   `desktop/loudvox_desktop/viewer/`. Reutilizá los assets de pdf.js copiándolos
   desde `extension/vendor/` (o moviéndolos a un lugar común — decidí y dejalo
   prolijo).
2. **Formatos:** PDF (pdf.js), TXT (texto plano), MD (markdown renderizado o
   texto limpio como en `files.py`), **DJVU** (extraé el texto con la capa de
   texto vía `djvulibre`/`djvutxt` si está disponible; si el DJVU es escaneado
   sin capa de texto, mostrá un aviso claro — el OCR queda fuera de alcance).
   Documentá en el README la dependencia de sistema `djvulibre` para DJVU.
3. **Pestañas de archivos** arriba (estilo Sumatra): abrir varios documentos,
   cambiar entre ellos, cerrar pestañas, y una lista de **archivos recientes**
   (persistida en `config_dir()/recent.json`). Reabrir un reciente con un clic.
4. **Lectura integrada** (esto es el corazón):
   - Botones grandes y accesibles: ▶ Leer todo · ⏩ Leer desde la selección ·
     🔊 Leer selección · ⏹ Detener.
   - **Resaltado** del párrafo que se está leyendo + auto-scroll (portá
     `viewer.js`/`content.js`).
   - Toma voz/velocidad/volumen/tono de `loudvox.config` (y respetá
     `params_for(voice)`), igual que el resto de la app.
   - Reproducción: reutilizá el enfoque del motor — la UI pide `/speak` al
     motor local y reproduce, **o** delegá la síntesis+reproducción al
     `player.py` de Python vía el bridge de pywebview. Elegí la opción más
     robusta y explicá por qué en un comentario. Debe haber **stop instantáneo**
     y lectura sin cortes entre párrafos (precarga del siguiente).
   - Letra grande ajustable (A−/A+), tema claro/oscuro deseable.
5. **Asociación de archivos (doble clic):** que se pueda poner LoudVox como app
   por defecto para .pdf/.txt/.md/.djvu, de forma **opcional** y reversible.
   - Windows: registro de asociaciones + un comando `loudvox-viewer <archivo>`.
   - Linux: archivo `.desktop` + MIME.
   - Integralo como paso **opcional** en `instalar.ps1` (el instalador ya existe
     en la raíz, en 4 idiomas) y documentá cómo revertirlo.
6. **Entrada por CLI:** `loudvox-viewer ruta/al/archivo` abre el visor con ese
   documento (esto es lo que invoca el doble clic). Agregá el entry point en
   `desktop/pyproject.toml`. Sin argumento, abre el visor vacío (con recientes).
7. **100% local, auditable, deps fijadas.** Nada de red salvo el motor en
   localhost. Sin telemetría.

## Cómo probar (obligatorio antes de dar por terminado)

El sandbox no tiene pantalla, así que la ventana pywebview no se puede abrir
ahí — pero **casi todo lo demás sí se testea**:

- **Extracción de texto**: tests unitarios de `extract_text` para pdf/txt/md/djvu
  (generá PDFs de prueba con reportlab como ya se hace en el repo; para DJVU,
  si no podés generar uno, mockeá `djvutxt` y testeá el parsing y el mensaje de
  "sin capa de texto").
- **La UI HTML/JS**: renderizala headless con **Playwright + Chromium**
  (`/opt/pw-browsers/chromium`), igual que los tests E2E de la extensión
  (`scratchpad/e2e_pdf_test.py` es el patrón): cargá un PDF real, verificá que
  extrae párrafos, que "leer todo" resalta y avanza contra el **motor real**
  (`loudvox serve` + una voz instalada), que "detener" limpia, y que las
  pestañas y recientes funcionan (estado en JS).
- **Lógica de pestañas / recientes / asociación**: tests unitarios (persistencia
  de `recent.json`, generación de los scripts de asociación).
- Corré TODAS las suites existentes (`engine/tests`, `desktop/tests`) y que
  sigan en verde.

## Definición de "terminado"

- Abre y muestra PDF, TXT, MD y DJVU (DJVU con capa de texto; aviso claro si no).
- Pestañas + archivos recientes funcionando.
- Lee en voz alta con resaltado y auto-scroll, respetando la config; stop
  instantáneo; sin cortes entre párrafos.
- `loudvox-viewer <archivo>` funciona; asociación de archivos integrada al
  instalador de forma opcional y reversible; entrada en la bandeja.
- README del visor con instalación, uso, la dependencia djvulibre y cómo
  asociar/desasociar tipos de archivo.
- Tests nuevos + los existentes en verde; E2E headless de la UI en verde.
- Commiteado y pusheado a `claude/readvox-research-slumjx`.
- Un reporte final honesto: qué verificaste automáticamente y qué queda
  pendiente de confirmar en una máquina con GUI (abrir la ventana real,
  el doble clic, la reproducción de audio en la ventana).

## Después (si el visor quedó completo y verificado): instalador .exe

Como segunda tarea, empaquetar la app como **.exe único para Windows** con
PyInstaller (que incluya motor + cliente + visor), **manteniendo** el
`instalar.ps1` transparente como alternativa para quien quiera ver qué corre.
Pero primero terminá el visor.

## Reglas de trabajo

- No rompas lo que ya anda (extensión, dictado, TTS, instalador, config).
- Verificá contra el código/fuentes reales antes de asumir APIs (no adivines
  firmas de pywebview ni de djvulibre: leé su doc/código). Si algo no se puede
  descargar en el sandbox por red bloqueada, decilo y pedí que se suba, no lo
  simules como si funcionara.
- Reutilizá agresivamente lo que ya existe (viewer.js, content.js, files.py,
  player.py, chunker.py, config).
- Commits chicos y frecuentes; push al terminar cada pieza grande.
