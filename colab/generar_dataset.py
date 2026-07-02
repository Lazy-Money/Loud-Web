"""Genera un dataset de entrenamiento Piper SIN grabar ni transcribir nada.

Sintetiza frases de un texto largo (un libro, artículos) con una voz que ya
tengas (Kokoro para destilar su calidad, o cualquier voz Piper) y arma el
dataset en formato LJSpeech listo para el notebook de Colab o el
entrenamiento local: wavs/ + metadata.csv, con transcripción perfecta
(el texto lo pusiste vos, no hay nada que transcribir).

Uso:
  python generar_dataset.py libro.txt --voice ef_dora --engine kokoro --minutes 30 -o dataset
  python generar_dataset.py libro.txt --voice es_ES-sharvard-medium --engine piper --minutes 20 -o dataset

Después: compactá la carpeta en dataset.zip y seguí con el notebook.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

TARGET_RATE = 22050  # lo que espera el entrenamiento de Piper


def split_sentences(text: str, min_chars: int = 30, max_chars: int = 220) -> list[str]:
    """Frases de 3-15 segundos aprox: ni muy cortas ni muy largas."""
    text = re.sub(r"\s+", " ", text)
    raw = re.split(r"(?<=[.!?…])\s+", text)
    out = []
    for s in raw:
        s = s.strip()
        if min_chars <= len(s) <= max_chars and not re.search(r"[|_#@{}<>\[\]]", s):
            out.append(s)
    return out


def resample_to_target(wav_bytes: bytes) -> tuple[bytes, float]:
    """WAV int16 mono a 22050 Hz. Devuelve (wav, duración_seg)."""
    import numpy as np

    with wave.open(io.BytesIO(wav_bytes)) as w:
        rate = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    if rate != TARGET_RATE:
        idx = np.linspace(0, len(data) - 1, int(len(data) * TARGET_RATE / rate))
        data = np.interp(idx, np.arange(len(data)), data).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TARGET_RATE)
        w.writeframes(data.tobytes())
    return buf.getvalue(), len(data) / TARGET_RATE


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("texto", help="archivo .txt largo (un libro, artículos)")
    ap.add_argument("--voice", required=True, help="voz origen (ef_dora, es_ES-sharvard-medium…)")
    ap.add_argument("--engine", choices=["kokoro", "piper"], default="kokoro")
    ap.add_argument("--speaker", type=int, default=None, help="hablante (voces multi-speaker)")
    ap.add_argument("--minutes", type=float, default=30, help="minutos de audio a generar")
    ap.add_argument("-o", "--out", default="dataset", help="carpeta de salida")
    args = ap.parse_args()

    from loudvox.config import load
    from loudvox.tts import get_backend

    cfg = load()
    backend = get_backend(args.engine, cfg.resolved_voices_dir())

    text = Path(args.texto).read_text(encoding="utf-8", errors="replace")
    sentences = split_sentences(text)
    if not sentences:
        print("No se extrajeron frases útiles del texto.", file=sys.stderr)
        return 1
    print(f"{len(sentences)} frases candidatas; objetivo: {args.minutes} min de audio")

    out = Path(args.out)
    wavs = out / "wavs"
    wavs.mkdir(parents=True, exist_ok=True)

    total = 0.0
    rows = []
    for i, sentence in enumerate(sentences):
        if total >= args.minutes * 60:
            break
        try:
            wav = backend.synthesize(sentence, args.voice, speaker=args.speaker)
        except Exception as exc:
            print(f"  [salteada] {sentence[:40]}… ({exc})")
            continue
        wav, seconds = resample_to_target(wav)
        if not 1.0 <= seconds <= 20.0:
            continue
        name = f"frase{i:05d}"
        (wavs / f"{name}.wav").write_bytes(wav)
        rows.append(f"{name}|{sentence}")
        total += seconds
        if len(rows) % 25 == 0:
            print(f"  {len(rows)} frases, {total/60:.1f} min")

    (out / "metadata.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"\nLISTO: {len(rows)} frases, {total/60:.1f} min en {out}/")
    print(f"Siguiente paso: comprimí '{out}' en dataset.zip y usá el notebook de Colab")
    return 0


if __name__ == "__main__":
    sys.exit(main())
