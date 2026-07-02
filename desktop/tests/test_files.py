import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from loudvox_desktop.files import extract_text, find_start


def test_txt(tmp_path):
    f = tmp_path / "nota.txt"
    f.write_text("Hola mundo", encoding="utf-8")
    assert extract_text(f) == "Hola mundo"

def test_md_limpia_sintaxis(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text(
        "# Título\n\nTexto con **negrita** y [enlace](http://x.com).\n\n"
        "- item uno\n\n```\ncodigo ignorado\n```\n",
        encoding="utf-8",
    )
    out = extract_text(f)
    assert "Título" in out and "negrita" in out and "enlace" in out
    assert "**" not in out and "http://x.com" not in out
    assert "codigo ignorado" not in out
    assert "- item" not in out and "item uno" in out

def test_pdf(tmp_path):
    # PDF mínimo generado con pypdf para no depender de binarios externos
    from pypdf import PdfWriter

    f = tmp_path / "doc.pdf"
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    with f.open("wb") as fh:
        w.write(fh)
    out = extract_text(f)  # página en blanco -> string vacío, sin excepción
    assert out == ""

def test_formato_no_soportado(tmp_path):
    f = tmp_path / "imagen.png"
    f.write_bytes(b"x")
    with pytest.raises(ValueError, match="no soportado"):
        extract_text(f)

def test_no_existe():
    with pytest.raises(FileNotFoundError):
        extract_text("/no/existe.txt")

def test_find_start():
    text = "Introducción. Capítulo uno: érase una vez."
    assert find_start(text, "capítulo uno") == "Capítulo uno: érase una vez."
    assert find_start(text, "no aparece") == text
