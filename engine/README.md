# LoudVox Engine

Motor local de texto a voz (TTS). **100% offline**: la única operación de red
es la descarga inicial de voces, que ejecutás vos explícitamente. Ninguna otra
parte del código toca internet, y el servidor escucha solo en `127.0.0.1`.

## Instalación

Requiere Python 3.9+ (Windows y Linux).

```bash
cd engine
pip install .
```

## Descargar voces (una sola vez, requiere internet)

```bash
loudvox download es    # voces recomendadas en español
loudvox download en    # inglés
loudvox download it    # italiano
loudvox download de    # alemán
# o una voz puntual:
loudvox download de_DE-thorsten-medium
```

Cada voz pesa ~20-75 MB y queda guardada localmente. Después de esto podés
desconectar internet: todo sigue funcionando.

## Uso

```bash
# Sintetizar a WAV (expande abreviaturas automáticamente)
loudvox speak "El Dr. García corrió 10 km en 45 min" -o salida.wav

# Velocidad: 0.25 (muy lento) a 4.0 (muy rápido)
loudvox speak "Hello world" -l en --speed 1.5 -o out.wav

# Ver la expansión de abreviaturas sin sintetizar
loudvox normalize "Mide 1,8 m y pesa 80 kg"
# -> Mide 1,8 metros y pesa 80 kilogramos

# Listar voces instaladas / configuración
loudvox voices
loudvox config

# Servidor local para la extensión y el cliente de escritorio
loudvox serve
```

## ¿CPU o GPU?

| | CPU (por defecto) | GPU (NVIDIA/CUDA) |
|---|---|---|
| Requisitos | Cualquier PC de los últimos ~10 años | Placa NVIDIA + drivers CUDA |
| Velocidad con Piper | Tiempo real o mejor, incluso en equipos modestos | Más rápida, pero Piper ya es rápido en CPU: diferencia poco perceptible |
| ¿Cuándo conviene? | Siempre, como punto de partida | Si vas a usar voces pesadas (Kokoro, clonación Chatterbox) o generar audios largos por lote |

**Recomendación**: empezá con CPU. Si más adelante activás los motores de las
fases siguientes y tenés placa NVIDIA, instalá el soporte GPU y activálo:

```bash
pip install .[gpu]        # reemplaza onnxruntime por la variante CUDA
loudvox speak "..." --gpu -o out.wav
```

O de forma permanente en la config (`loudvox config` muestra la ruta del
archivo): `"use_gpu": true`. Es reversible en cualquier momento.

## Motor Kokoro (voz premium, opcional)

Kokoro-82M suena notablemente más natural que Piper y sigue siendo
CPU-friendly (aunque más lento: úsalo si tu PC va sobrada con Piper).
Sin alemán en v1.0 (para `de`, seguí con Piper).

```bash
pip install .[kokoro]        # instala el runtime
loudvox download kokoro      # baja el modelo (~340 MB, una vez)
```

En `config.json`: `"engine": "kokoro"` y una voz Kokoro, p. ej.
`"voice": "ef_dora"` (es), `em_alex` (es), `af_heart` (en), `if_sara` (it).
`loudvox voices` lista las instaladas. Para volver a Piper:
`"engine": "piper"`.

## Diccionarios de abreviaturas

En `dictionaries/` hay un CSV por idioma (`es`, `en`, `it`, `de`) con el formato:

```csv
abreviatura,expansión_singular,expansión_plural,modo
m,metro,metros,unit
Dr.,Doctor,,word
```

- `unit`: solo se expande después de un número (`10 m` → `10 metros`,
  `1 m` → `1 metro`; una "m" suelta no se toca).
- `word`: se expande siempre como palabra completa (`Dr.` → `Doctor`).

**Tus propios diccionarios**: creá `~/.local/share/loudvox/dictionaries/es.csv`
(Linux) o `%LOCALAPPDATA%\loudvox\dictionaries\es.csv` (Windows) con el mismo
formato. Tus entradas tienen prioridad sobre las incluidas.

## Configuración

`loudvox config` muestra los valores actuales y la ruta del JSON. Campos:

- `language`: `es` | `en` | `it` | `de`
- `voice`: nombre de voz Piper (vacío = recomendada del idioma)
- `speed`: velocidad de lectura (1.0 normal, 0.5–3.0)
- `volume`: volumen (1.0 normal, 0.1–2.0)
- `pitch`: tono en semitonos — negativo = más grave, positivo = más agudo
  (rango útil ±6; también por voz en `voice_overrides`). Se aplica sin
  cambiar la velocidad.
- `use_gpu`: `true`/`false`
- `hotkeys`: combinaciones personalizables, mínimo 2 teclas
  (`"ctrl+alt+r"`); sin restricciones sobre cuáles.
- `voice_overrides`: ajustes por voz que pisan a los globales. Ideal para
  emparejar voces que suenan más fuerte o más rápido que otras:

```json
"voice_overrides": {
  "es_ES-davefx-medium":   { "volume": 0.6, "speed": 1.1 },
  "es_ES-sharvard-medium": { "speaker": 0 }
}
```

(`speaker` elige el hablante en voces multi-hablante como sharvard.)
La precedencia es: pedido explícito (p. ej. el deslizador de la extensión)
> override de la voz > global.

## Tests

```bash
pip install .[dev]
python -m pytest tests/
```

## API local (para la extensión y el cliente de escritorio)

`loudvox serve` levanta `http://127.0.0.1:5089` (solo accesible desde tu
máquina):

- `GET /health` — estado y versión
- `GET /voices` — voces instaladas
- `POST /normalize` — `{"text": "...", "language": "es"}` → texto expandido
- `POST /speak` — `{"text": "...", "voice": "...", "speed": 1.2}` → WAV

No se registra ningún contenido: el servidor no loguea lo que leés ni dictás.
