"""Servidor HTTP local de LoudVox.

Escucha SOLO en 127.0.0.1 (nunca expuesto a la red). Implementado con la
biblioteca estándar de Python: cero dependencias de servidor que auditar.

Endpoints:
  GET  /health              -> {"status": "ok", "version": ...}
  GET  /voices              -> {"voices": [...], "language": ..., "default_voice": ...}
  POST /normalize {text, language?}          -> {"text": "..."}
  POST /speak {text, voice?, language?, speed?, normalize?} -> audio/wav
"""

from __future__ import annotations

import json
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__
from .config import Config, load
from .normalizer import Normalizer
from .tts import get_backend

MAX_BODY = 1_000_000  # 1 MB de texto es más que suficiente


@lru_cache(maxsize=8)
def _normalizer(lang: str) -> Normalizer:
    return Normalizer.for_language(lang)


class _Handler(BaseHTTPRequestHandler):
    # Inyectados por serve():
    cfg: Config = Config()
    backend = None

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_BODY:
            raise ValueError(f"Cuerpo demasiado grande ({length} bytes)")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:  # noqa: N802 (nombre exigido por http.server)
        if self.path == "/health":
            self._json(200, {"status": "ok", "version": __version__})
        elif self.path == "/voices":
            self._json(
                200,
                {
                    "voices": self.backend.list_voices(),
                    "language": self.cfg.language,
                    "default_voice": self.cfg.resolved_voice(),
                },
            )
        else:
            self._json(404, {"error": f"Ruta desconocida: {self.path}"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            data = self._read_body()
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
            return

        if self.path == "/normalize":
            lang = data.get("language", self.cfg.language)
            try:
                text = _normalizer(lang).normalize(data.get("text", ""))
            except Exception as exc:
                self._json(400, {"error": str(exc)})
                return
            self._json(200, {"text": text})

        elif self.path == "/speak":
            text = data.get("text", "").strip()
            if not text:
                self._json(400, {"error": "Falta 'text'"})
                return
            lang = data.get("language", self.cfg.language)
            voice = data.get("voice") or self.cfg.resolved_voice()
            # Precedencia: pedido explícito > override por voz > global
            params = self.cfg.params_for(voice)
            speed = float(data.get("speed") or params["speed"])
            volume = float(data.get("volume") or params["volume"])
            pitch = float(data.get("pitch", params["pitch"]))
            if data.get("normalize", True):
                text = _normalizer(lang).normalize(text)
            try:
                wav = self.backend.synthesize(
                    text, voice, speed=speed, volume=volume, speaker=params["speaker"]
                )
                if pitch:
                    from .audio import apply_pitch

                    wav = apply_pitch(wav, pitch)
            except (FileNotFoundError, ValueError) as exc:
                self._json(400, {"error": str(exc)})
                return
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(wav)))
            self.end_headers()
            self.wfile.write(wav)

        else:
            self._json(404, {"error": f"Ruta desconocida: {self.path}"})

    def log_message(self, fmt: str, *args) -> None:
        # Sin logs de contenido: lo que leés/dictás no queda registrado.
        pass


def serve(port: int = 5089, cfg: Config | None = None) -> None:
    cfg = cfg or load()
    handler = type("Handler", (_Handler,), {})
    handler.cfg = cfg
    handler.backend = get_backend(
        cfg.engine, cfg.resolved_voices_dir(), use_gpu=cfg.use_gpu
    )
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"LoudVox escuchando en http://127.0.0.1:{port} (solo local)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")
