"""Divide texto largo en fragmentos cortos para síntesis con baja latencia.

Corta por párrafos y, dentro de cada párrafo, por oraciones, agrupando hasta
``max_chars``. Así el audio empieza a sonar enseguida y el fragmento
siguiente se sintetiza mientras suena el actual.
"""

from __future__ import annotations

import re

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+|(?<=[:;])\s+(?=[A-ZÁÉÍÓÚÜÑ¿¡])")


def chunk_text(text: str, max_chars: int = 400) -> list[str]:
    chunks: list[str] = []
    for para in re.split(r"\n\s*\n|\r\n\s*\r\n", text):
        para = re.sub(r"\s+", " ", para).strip()
        if not para:
            continue
        sentences = _SENTENCE_END.split(para)
        current = ""
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if current and len(current) + len(s) + 1 > max_chars:
                chunks.append(current)
                current = s
            else:
                current = f"{current} {s}".strip()
            # Oración individual más larga que el máximo: cortar por comas
            while len(current) > max_chars:
                cut = current.rfind(",", 0, max_chars)
                cut = cut if cut > max_chars // 3 else max_chars
                chunks.append(current[:cut].strip())
                current = current[cut:].lstrip(", ")
        if current:
            chunks.append(current)
    return chunks
