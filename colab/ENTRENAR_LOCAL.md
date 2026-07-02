# Entrenar tu voz 100% local (sin internet, sin Colab)

Alternativa completamente offline al notebook de Colab, usando **tu propia
GPU NVIDIA** (la misma que ya usás para el dictado). El proceso pesado corre
una sola vez en tu máquina; el resultado es el mismo archivo `.onnx` liviano.

> Requisitos: GPU NVIDIA con ≥8 GB de VRAM, ~10 GB de disco libre, y
> paciencia (3-6 horas de entrenamiento). Internet solo hace falta UNA vez
> para bajar las herramientas y el checkpoint base — después, todo offline
> para siempre (podés bajarlos en otra máquina y pasarlos por pendrive).

## Por qué WSL2

El pipeline de entrenamiento de Piper (`piper_train`) está hecho para Linux.
En Windows, la vía soportada es **WSL2** (el Linux integrado de Windows, con
acceso directo a tu GPU NVIDIA — los drivers de Windows ya lo soportan).

```powershell
# Una vez, como administrador:
wsl --install -d Ubuntu-22.04
```

## Pasos (dentro de Ubuntu/WSL2)

```bash
# 1. Herramientas (única descarga junto con el paso 3)
sudo apt update && sudo apt install -y python3.10-venv espeak-ng git build-essential
python3 -m venv ~/piper-env && source ~/piper-env/bin/activate

# 2. Piper training
git clone https://github.com/rhasspy/piper.git ~/piper
cd ~/piper/src/python
pip install -e .
pip install "pytorch-lightning~=1.9" "numpy<2" onnxruntime librosa espeak-phonemizer
bash build_monotonic_align.sh

# 3. Checkpoint base español (una vez; ~800 MB)
wget -O ~/base_es.ckpt "https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/main/es/es_ES/davefx/medium/epoch%3D2218-step%3D562840.ckpt"

# 4. Tu dataset (mismo formato que el de Colab: wavs/ + metadata.csv,
#    ver README.md de esta carpeta). Desde Windows es accesible en /mnt/c/...
DATASET=/mnt/c/Users/TU_USUARIO/Documents/mi_dataset

# 5. Preprocesar
python -m piper_train.preprocess \
  --language es --input-dir "$DATASET" --output-dir ~/train_out \
  --dataset-format ljspeech --single-speaker --sample-rate 22050

# 6. Entrenar (3-6 h según GPU; podés cortarlo y retomar)
python -m piper_train \
  --dataset-dir ~/train_out --accelerator gpu --devices 1 \
  --batch-size 16 --validation-split 0.0 --num-test-examples 0 \
  --max_epochs 2600 --resume_from_checkpoint ~/base_es.ckpt \
  --checkpoint-epochs 5 --precision 32 --quality medium

# 7. Exportar e instalar
python -m piper_train.export_onnx \
  ~/train_out/lightning_logs/version_0/checkpoints/*.ckpt /mnt/c/Users/TU_USUARIO/mi_voz.onnx
cp ~/train_out/config.json /mnt/c/Users/TU_USUARIO/mi_voz.onnx.json
```

Copiá ambos archivos a tu carpeta de voces de LoudVox y elegí `mi_voz` en
Configuración. Listo: tu voz, entrenada y ejecutada sin que un solo byte
salga de tu casa.

## Alternativa sin entrenamiento: clonación instantánea (Chatterbox)

Si preferís no grabar 15-30 minutos, **Chatterbox** (Resemble AI, MIT) clona
con ~10 segundos de muestra, 100% local — pero el modelo (~500M parámetros)
corre en tu GPU **en cada lectura**, no una sola vez. Con tu placa
funcionaría; el costo es velocidad y VRAM permanentes en vez de un
entrenamiento único. Si te interesa, se integra como motor opcional
(igual que Kokoro).

| | Piper entrenado (esta guía) | Chatterbox zero-shot |
|---|---|---|
| Muestra necesaria | 15-60 min grabados | ~10 segundos |
| Esfuerzo único | 3-6 h de entrenamiento | ninguno |
| Costo por lectura | casi nulo (CPU) | alto (GPU siempre) |
| Fidelidad | muy buena con buen dataset | buena |
