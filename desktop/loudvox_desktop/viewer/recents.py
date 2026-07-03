"""Archivos recientes del visor, persistidos en config_dir()/recent.json."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from loudvox.config import config_dir

MAX_RECENTS = 12
_lock = threading.Lock()


def _path() -> Path:
    return config_dir() / "recent.json"


def load() -> list[dict]:
    """Lista de {path, title, ts}, más reciente primero. Tolerante a roturas."""
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [
                d for d in data
                if isinstance(d, dict) and isinstance(d.get("path"), str)
            ][:MAX_RECENTS]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def add(path: str, title: str) -> list[dict]:
    """Agrega/asciende un archivo y devuelve la lista actualizada."""
    with _lock:
        items = [d for d in load() if d["path"] != path]
        items.insert(0, {"path": path, "title": title, "ts": int(time.time())})
        items = items[:MAX_RECENTS]
        p = _path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        return items


def existing() -> list[dict]:
    """Solo los recientes cuyos archivos siguen existiendo en disco."""
    return [d for d in load() if Path(d["path"]).exists()]
