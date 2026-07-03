"""Tests de recientes (persistencia) y del bridge del visor (sin ventana)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from loudvox_desktop.viewer import recents
from loudvox_desktop.viewer.bridge import ViewerApi


@pytest.fixture(autouse=True)
def _config_en_tmp(tmp_path, monkeypatch):
    """Aísla config_dir() para no tocar la config real del usuario."""
    monkeypatch.setattr(recents, "config_dir", lambda: tmp_path / "cfg")
    yield


class TestRecents:
    def test_vacio_al_inicio(self):
        assert recents.load() == []

    def test_agrega_y_ordena_mas_reciente_primero(self):
        recents.add("/a.txt", "a.txt")
        recents.add("/b.txt", "b.txt")
        items = recents.load()
        assert [d["path"] for d in items] == ["/b.txt", "/a.txt"]

    def test_reabrir_asciende_sin_duplicar(self):
        recents.add("/a.txt", "a.txt")
        recents.add("/b.txt", "b.txt")
        recents.add("/a.txt", "a.txt")
        items = recents.load()
        assert [d["path"] for d in items] == ["/a.txt", "/b.txt"]

    def test_tope_de_elementos(self):
        for i in range(20):
            recents.add(f"/f{i}.txt", f"f{i}.txt")
        assert len(recents.load()) == recents.MAX_RECENTS

    def test_json_roto_no_explota(self, tmp_path):
        p = tmp_path / "cfg" / "recent.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{basura", encoding="utf-8")
        assert recents.load() == []
        recents.add("/a.txt", "a.txt")  # y se recupera escribiendo de nuevo
        assert len(recents.load()) == 1

    def test_existing_filtra_archivos_borrados(self, tmp_path):
        real = tmp_path / "existe.txt"
        real.write_text("hola", encoding="utf-8")
        recents.add(str(real), real.name)
        recents.add("/ya/no/existe.txt", "existe.txt")
        assert [d["path"] for d in recents.existing()] == [str(real)]


class TestViewerApi:
    def test_open_path_txt(self, tmp_path):
        f = tmp_path / "nota.txt"
        f.write_text("Hola mundo.\n\nSegundo párrafo.", encoding="utf-8")
        api = ViewerApi()
        doc = api.open_path(str(f))
        assert doc["ok"] is True
        assert doc["title"] == "nota.txt"
        assert doc["paragraphs"] == ["Hola mundo.", "Segundo párrafo."]
        # quedó en recientes
        assert [d["path"] for d in api.get_recents()] == [str(f)]

    def test_open_path_error_claro_y_sin_reciente(self, tmp_path):
        api = ViewerApi()
        doc = api.open_path(str(tmp_path / "no_existe.pdf"))
        assert doc["ok"] is False and doc["error"]
        assert api.get_recents() == []

    def test_get_boot_trae_strings_y_documento_inicial(self, tmp_path):
        f = tmp_path / "inicial.txt"
        f.write_text("Contenido inicial.", encoding="utf-8")
        api = ViewerApi(initial_path=str(f))
        boot = api.get_boot()
        assert boot["strings"]["vw_read_all"]  # UI traducida desde Python
        assert boot["initial"]["ok"] is True
        assert boot["initial"]["paragraphs"] == ["Contenido inicial."]
        # el inicial se consume una sola vez (recargar la UI no lo re-abre)
        assert api.get_boot()["initial"] is None

    def test_read_text_vacio(self):
        api = ViewerApi()
        assert api.read_text("   ")["ok"] is False

    def test_stop_sin_lector_no_falla(self):
        assert ViewerApi().stop() == {"ok": True}
