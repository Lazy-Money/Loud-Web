# Voces personalizadas para LoudVox

Dos caminos para tener voces propias, ambos con GPU gratuita de Google Colab.
El resultado siempre es un par de archivos `.onnx` + `.onnx.json` (~60 MB) que
copiás a tu carpeta de voces de LoudVox y elegís en Configuración → Voz.

## Camino 1 — Destilar una voz Kokoro (sin grabar nada)

Notebook: **[destilar_alex.ipynb](destilar_alex.ipynb)** — genera una voz Piper
con el timbre de la voz Kokoro **Alex** (masculina, español). Kokoro lee el
guion, se arma el dataset solo, se entrena. Cero grabación, cero transcripción.

Abrir en Colab (Entorno de ejecución → GPU T4 antes de correr):
https://colab.research.google.com/github/Lazy-Money/Loud-Web/blob/claude/readvox-research-slumjx/colab/destilar_alex.ipynb

## Camino 2 — Clonar TU voz

Notebook: **[clonar_mi_voz.ipynb](clonar_mi_voz.ipynb)** — entrena con tus
grabaciones. Usás el mismo guion (`corpus/corpus_es_1300.txt`).

**Cómo grabar:** un clip corto por frase, nombrado por el número de la frase:
- `f00001.wav` = tu voz leyendo la línea 1 del corpus
- `f00002.wav` = línea 2, etc.

Grabás las que quieras y comprimís la carpeta en `dataset.zip`. El notebook
usa solo las que subas y arma el `metadata.csv` solo (ya sabemos el texto).

| Grabás | Tu voz | Resultado |
|---|---|---|
| ~300 frases | ~30-45 min | voz reconocible (prueba) |
| ~500 frases | ~1 h | buena |
| 1.300 frases | ~1,5-2 h | máxima fidelidad |

**Audio:** WAV mono, mismo micrófono/distancia, lugar silencioso, voz natural,
cada clip 1-15 s. El **grabador guiado de LoudVox** (a pedido) produce estos
archivos con el nombre correcto automáticamente: te muestra cada frase, grabás,
pasa a la siguiente.

## El corpus (guion)

`corpus/corpus_es_1300.txt` — 1.300 frases seleccionadas de Mozilla Common
Voice (dominio público) por cobertura de difonemas del español, sin nombres
extranjeros. Método reproducible en `corpus/generar_corpus.py`.

## Entrenar sin internet (opcional)

`ENTRENAR_LOCAL.md`: el mismo pipeline en tu propia GPU vía WSL2, sin nube.
