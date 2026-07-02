# Clonar tu voz para LoudVox (gratis, con Google Colab)

Entrenás una voz Piper con grabaciones tuyas usando la GPU gratuita de
Colab. El resultado es un archivo `.onnx` (~60 MB) que corre **local y
rápido en tu PC para siempre** — el proceso pesado ocurre una sola vez,
afuera.

> Estado: **beta**. El proceso funciona pero requiere paciencia (2-4 horas
> de Colab) y puede necesitar ajustes según los cambios de Colab.

## Paso 1 — Grabar tu voz (lo más importante)

**Cantidad**: mínimo 15 minutos de audio limpio; ideal 30-60 min.
Más audio = voz más fiel.

**Cómo grabar**:
- Habitación silenciosa, siempre el mismo micrófono y la misma distancia.
- Hablá natural, como si leyeras para otra persona (así va a sonar la voz).
- Frases de 3 a 15 segundos. Evitá ruidos, música, y de fondo la tele.
- Formato: WAV mono. Audacity (gratis) sirve perfecto.

**Qué leer**: cualquier texto variado (noticias, un libro). Cuanta más
variedad de palabras y entonaciones, mejor.

## Paso 2 — Armar el dataset

Una carpeta con esta estructura, comprimida en `dataset.zip`:

```
dataset/
├── wavs/
│   ├── frase001.wav
│   ├── frase002.wav
│   └── …
└── metadata.csv
```

`metadata.csv`: una línea por audio, con el texto EXACTO que se dice
(formato LJSpeech, separador `|`):

```
frase001|Hola, esta es la primera frase que grabé.
frase002|El clima de hoy está soleado y agradable.
```

## Paso 3 — Entrenar en Colab

1. Abrí `entrenar_voz_piper.ipynb` en [Google Colab](https://colab.research.google.com/)
   (Archivo → Subir notebook).
2. Entorno de ejecución → Cambiar tipo → **GPU (T4)**.
3. Ejecutá las celdas en orden. Te va a pedir subir `dataset.zip`.
4. El entrenamiento parte del checkpoint español oficial (fine-tuning):
   2-4 horas para un buen resultado.
5. La última celda descarga `mi_voz.onnx` + `mi_voz.onnx.json`.

## Paso 4 — Instalar tu voz en LoudVox

Copiá los dos archivos a la carpeta de voces (la muestra `loudvox config`
→ `voices_dir`; por defecto `%LOCALAPPDATA%\loudvox\voices` en Windows) y
en `config.json`:

```json
"voice": "mi_voz"
```

Reiniciá `loudvox-desktop`. Tu voz, 100% local.

## Alternativa sin entrenamiento (PC potente)

Chatterbox (Resemble AI, MIT) clona con 10 segundos de muestra, pero el
modelo completo (~500M params) debe correr en tu máquina en cada lectura:
solo tiene sentido con GPU buena. Si te interesa, es un módulo futuro.
