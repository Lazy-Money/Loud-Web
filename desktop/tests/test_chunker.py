import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loudvox_desktop.chunker import chunk_text


def test_texto_corto_un_fragmento():
    assert chunk_text("Hola mundo.") == ["Hola mundo."]

def test_respeta_parrafos():
    chunks = chunk_text("Primer párrafo.\n\nSegundo párrafo.")
    assert chunks == ["Primer párrafo.", "Segundo párrafo."]

def test_agrupa_oraciones_hasta_max():
    text = "Una oración. " * 10
    chunks = chunk_text(text, max_chars=60)
    assert all(len(c) <= 60 for c in chunks)
    assert " ".join(chunks).count("Una oración.") == 10

def test_oracion_larguisima_se_corta():
    text = "palabra, " * 100
    chunks = chunk_text(text, max_chars=100)
    assert len(chunks) > 1
    assert all(len(c) <= 120 for c in chunks)

def test_texto_vacio():
    assert chunk_text("") == []
    assert chunk_text("\n\n  \n") == []

def test_normaliza_espacios():
    assert chunk_text("hola\n   mundo") == ["hola mundo"]
