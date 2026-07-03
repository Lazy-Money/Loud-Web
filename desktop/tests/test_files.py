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


# ---------- párrafos (para el visor) ----------

from loudvox_desktop.files import (  # noqa: E402
    MissingToolError,
    NoTextLayerError,
    extract_paragraphs,
    to_paragraphs,
)


class TestToParagraphs:
    def test_linea_en_blanco_corta(self):
        assert to_paragraphs("Uno.\n\nDos.") == ["Uno.", "Dos."]

    def test_renglones_visuales_se_unen(self):
        # pypdf corta renglones a mitad de oración: deben unirse
        text = "El clima invernal varía de\nmoderadamente templado a frío."
        assert to_paragraphs(text) == [
            "El clima invernal varía de moderadamente templado a frío."
        ]

    def test_fin_de_oracion_mas_mayuscula_corta(self):
        text = "Primera oración completa.\nSegunda que empieza aparte."
        assert to_paragraphs(text) == [
            "Primera oración completa.",
            "Segunda que empieza aparte.",
        ]

    def test_minuscula_tras_punto_no_corta(self):
        # abreviatura a fin de renglón: "etc." + minúscula sigue unida
        text = "Compró frutas, verduras, etc.\ny también algo de pan."
        assert to_paragraphs(text) == [
            "Compró frutas, verduras, etc. y también algo de pan."
        ]

    def test_restos_de_una_letra_se_descartan(self):
        assert to_paragraphs("Párrafo real.\n\n7\n\nOtro párrafo.") == [
            "Párrafo real.",
            "Otro párrafo.",
        ]


# ---------- DJVU (con djvulibre real si está instalado) ----------

import shutil as _shutil  # noqa: E402
import subprocess as _sub  # noqa: E402

_HAS_DJVU = all(_shutil.which(t) for t in ("c44", "djvused", "djvutxt"))


def _make_djvu(tmp_path, with_text: bool):
    ppm = tmp_path / "page.ppm"
    with ppm.open("wb") as f:
        f.write(b"P6 100 100 255 ")
        f.write(bytes([200, 200, 200]) * (100 * 100))
    djvu = tmp_path / ("con_texto.djvu" if with_text else "sin_texto.djvu")
    _sub.run(["c44", str(ppm), str(djvu)], check=True, capture_output=True)
    if with_text:
        dsed = tmp_path / "t.dsed"
        dsed.write_text(
            'select 1\nset-txt\n(page 0 0 100 100\n'
            '  (line 0 60 100 80 (word 0 60 45 80 "Hola") (word 50 60 100 80 "mundo."))\n'
            '  (line 0 20 100 40 (word 0 20 60 40 "Segunda") (word 65 20 100 40 "parte.")))\n.\n',
            encoding="utf-8",
        )
        _sub.run(["djvused", str(djvu), "-f", str(dsed), "-s"],
                 check=True, capture_output=True)
    return djvu


@pytest.mark.skipif(not _HAS_DJVU, reason="djvulibre no instalado")
def test_djvu_con_capa_de_texto(tmp_path):
    djvu = _make_djvu(tmp_path, with_text=True)
    out = extract_text(djvu)
    assert "Hola mundo" in out and "Segunda parte" in out
    paras = extract_paragraphs(djvu)
    assert paras == ["Hola mundo.", "Segunda parte."]


@pytest.mark.skipif(not _HAS_DJVU, reason="djvulibre no instalado")
def test_djvu_sin_capa_de_texto_avisa(tmp_path):
    djvu = _make_djvu(tmp_path, with_text=False)
    with pytest.raises(NoTextLayerError, match="escaneo sin capa de texto"):
        extract_text(djvu)


def test_djvu_sin_djvulibre_mensaje_claro(tmp_path, monkeypatch):
    import loudvox_desktop.files as files_mod

    monkeypatch.setattr(files_mod.shutil, "which", lambda _t: None)
    f = tmp_path / "x.djvu"
    f.write_bytes(b"AT&TFORM")
    with pytest.raises(MissingToolError, match="djvulibre"):
        extract_text(f)
