"""Interfaz de línea de comandos de LoudVox.

Ejemplos:
  loudvox speak "Corrió 10 km en 45 min" -o salida.wav
  loudvox speak "Hello Dr. Smith" -l en --speed 1.5 -o out.wav
  loudvox normalize "El Dr. García mide 1,8 m"
  loudvox voices
  loudvox download es           # voces recomendadas de un idioma
  loudvox download es_ES-davefx-medium
  loudvox serve
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import RECOMMENDED_VOICES, SUPPORTED_LANGUAGES, load, save
from .normalizer import Normalizer
from .tts import get_backend


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except (FileNotFoundError, ValueError, NotImplementedError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="loudvox", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_speak = sub.add_parser("speak", help="sintetizar texto a WAV")
    p_speak.add_argument("text", nargs="?", help="texto (o - para stdin)")
    p_speak.add_argument("-l", "--language", choices=SUPPORTED_LANGUAGES)
    p_speak.add_argument("-v", "--voice", help="voz Piper instalada")
    p_speak.add_argument("--speed", type=float, help="1.0 normal, 2.0 doble")
    p_speak.add_argument("-o", "--output", required=True, help="archivo WAV de salida")
    p_speak.add_argument("--no-normalize", action="store_true")
    p_speak.add_argument("--gpu", action="store_true", help="usar CUDA si está disponible")

    p_norm = sub.add_parser("normalize", help="solo expandir abreviaturas")
    p_norm.add_argument("text")
    p_norm.add_argument("-l", "--language", choices=SUPPORTED_LANGUAGES)

    sub.add_parser("voices", help="listar voces instaladas")

    p_dl = sub.add_parser("download", help="descargar voces (requiere internet)")
    p_dl.add_argument("target", help="idioma (es|en|it|de) o nombre de voz")

    p_serve = sub.add_parser("serve", help="iniciar servidor local")
    p_serve.add_argument("--port", type=int, default=5089)

    sub.add_parser("config", help="mostrar configuración actual y su ruta")

    args = parser.parse_args(argv)
    cfg = load()

    if args.command == "speak":
        text = sys.stdin.read() if args.text in (None, "-") else args.text
        lang = args.language or cfg.language
        voice = args.voice or (
            RECOMMENDED_VOICES[lang][0] if args.language else cfg.resolved_voice()
        )
        speed = args.speed if args.speed is not None else cfg.speed
        if not args.no_normalize:
            text = Normalizer.for_language(lang).normalize(text)
        backend = get_backend(
            cfg.engine, cfg.resolved_voices_dir(), use_gpu=args.gpu or cfg.use_gpu
        )
        wav = backend.synthesize(text, voice, speed=speed)
        Path(args.output).write_bytes(wav)
        print(f"OK: {args.output} ({len(wav)} bytes, voz {voice}, velocidad {speed})")

    elif args.command == "normalize":
        lang = args.language or cfg.language
        print(Normalizer.for_language(lang).normalize(args.text))

    elif args.command == "voices":
        backend = get_backend(cfg.engine, cfg.resolved_voices_dir())
        installed = backend.list_voices()
        if installed:
            for v in installed:
                marker = " (por defecto)" if v == cfg.resolved_voice() else ""
                print(f"  {v}{marker}")
        else:
            print(
                f"No hay voces en {cfg.resolved_voices_dir()}.\n"
                f"Descargá con: loudvox download {cfg.language}"
            )

    elif args.command == "download":
        from .downloader import download_kokoro, download_language, download_voice

        dest = cfg.resolved_voices_dir()
        if args.target == "kokoro":
            download_kokoro(dest)
        elif args.target in SUPPORTED_LANGUAGES:
            download_language(args.target, dest)
        else:
            download_voice(args.target, dest)
        print(f"Voces en: {dest}")

    elif args.command == "serve":
        from .server import serve

        serve(port=args.port, cfg=cfg)

    elif args.command == "config":
        from dataclasses import asdict
        import json

        path = save(cfg)  # crea el archivo con defaults si no existía
        print(json.dumps(asdict(cfg), indent=2, ensure_ascii=False))
        print(f"\nArchivo: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
