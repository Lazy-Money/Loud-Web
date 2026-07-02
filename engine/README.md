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
- `speed`: velocidad de lectura (1.0 normal)
- `pitch`: tono en semitonos (Fase 5)
- `use_gpu`: `true`/`false`
- `hotkeys`: combinaciones personalizables, mínimo 2 teclas
  (`"ctrl+alt+r"`); sin restricciones sobre cuáles.

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
