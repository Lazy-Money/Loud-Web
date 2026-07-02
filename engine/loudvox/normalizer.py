"""Normalización de texto previa a la síntesis.

Expande abreviaturas usando diccionarios CSV por idioma. Dos modos de entrada:

  - ``unit``: solo se expande cuando la abreviatura sigue a un número
    ("10 m" -> "10 metros", "1 m" -> "1 metro"; una "m" suelta no se toca).
  - ``word``: se expande siempre que aparezca como palabra completa
    ("Dr. García" -> "Doctor García").

Formato CSV (UTF-8, separador coma, ``#`` para comentarios)::

    abreviatura,expansión_singular,expansión_plural,modo

``expansión_plural`` puede quedar vacía (se usa la singular). El usuario puede
añadir sus propios diccionarios en ``data_dir()/dictionaries/<lang>.csv``; sus
entradas tienen prioridad sobre las incluidas con la aplicación.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .config import data_dir

BUNDLED_DIR = Path(__file__).resolve().parent.parent / "dictionaries"

# Número con decimales estilo europeo (1,5) o anglosajón (1.5), y miles.
_NUM = r"\d+(?:[.,]\d+)*"


@dataclass(frozen=True)
class Entry:
    abbrev: str
    singular: str
    plural: str
    mode: str  # "unit" | "word"


def parse_csv(path: Path) -> list[Entry]:
    entries: list[Entry] = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.reader(fh):
            if not row or row[0].lstrip().startswith("#"):
                continue
            if len(row) < 4:
                raise ValueError(f"{path.name}: fila inválida {row!r} (se esperan 4 columnas)")
            abbrev, singular, plural, mode = (c.strip() for c in row[:4])
            mode = mode.lower()
            if mode not in ("unit", "word"):
                raise ValueError(f"{path.name}: modo desconocido {mode!r} en {row!r}")
            entries.append(Entry(abbrev, singular, plural or singular, mode))
    return entries


def _is_singular(number: str) -> bool:
    """'1' es singular; '1,5', '10', '1.000' no lo son."""
    return re.fullmatch(r"0*1", number) is not None


class Normalizer:
    def __init__(self, entries: list[Entry]):
        # Las abreviaturas más largas primero, para que "km" gane sobre "m".
        self._entries = sorted(entries, key=lambda e: len(e.abbrev), reverse=True)
        self._compiled: list[tuple[re.Pattern[str], Entry]] = []
        for e in self._entries:
            esc = re.escape(e.abbrev)
            if e.mode == "unit":
                # Número + espacios opcionales + abreviatura ("10 m" y "10m").
                # No hace falta límite izquierdo: solo puede haber espacios
                # entre el número y la abreviatura.
                pat = re.compile(rf"(?P<num>{_NUM})\s*{esc}(?![\w.])")
            else:
                # Palabra completa. El punto final de la abreviatura ("Dr.")
                # forma parte del patrón, no del límite.
                pat = re.compile(rf"(?<![\w]){esc}(?![\w])")
            self._compiled.append((pat, e))

    @classmethod
    def for_language(cls, lang: str, extra_paths: list[Path] | None = None) -> "Normalizer":
        """Carga el diccionario incluido + el del usuario si existe."""
        entries: list[Entry] = []
        bundled = BUNDLED_DIR / f"{lang}.csv"
        if bundled.exists():
            entries.extend(parse_csv(bundled))
        user = data_dir() / "dictionaries" / f"{lang}.csv"
        paths = ([user] if user.exists() else []) + (extra_paths or [])
        seen_user: set[str] = set()
        user_entries: list[Entry] = []
        for p in paths:
            for e in parse_csv(p):
                user_entries.append(e)
                seen_user.add(e.abbrev)
        # Prioridad usuario: se descartan las incluidas que colisionen.
        entries = [e for e in entries if e.abbrev not in seen_user] + user_entries
        return cls(entries)

    def normalize(self, text: str) -> str:
        for pat, entry in self._compiled:
            if entry.mode == "unit":

                def repl(m: re.Match[str], _e: Entry = entry) -> str:
                    num = m.group("num")
                    word = _e.singular if _is_singular(num) else _e.plural
                    return f"{num} {word}"

                text = pat.sub(repl, text)
            else:
                text = pat.sub(entry.singular, text)
        return text
