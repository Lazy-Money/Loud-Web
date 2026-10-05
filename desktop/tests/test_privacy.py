"""Garantías de privacidad: nada de lo leído/dictado queda en disco.

1. El log de diagnóstico no acumula historial (se reinicia por arranque).
2. El historial de recientes del visor se puede desactivar y borrar.
3. Los .wav temporales de reproducción se barren aunque haya habido un crash.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "engine"))

import pytest


# ---------- 1) log efímero y sin contenido ----------

def test_log_se_reinicia_en_cada_arranque(tmp_path, monkeypatch):
    import loudvox.config as lcfg
    import loudvox_desktop.cli as cli

    monkeypatch.setattr(lcfg, "data_dir", lambda: tmp_path)
    log = tmp_path / "loudvox.log"
    log.write_text("sesion anterior: esto NO debe sobrevivir\n", encoding="utf-8")

    out, err = sys.stdout, sys.stderr
    try:
        sys.stdout = None  # así arranca pythonw
        sys.stderr = None
        cli._setup_headless_io()
        assert log.read_text(encoding="utf-8") == ""  # modo "w": vacío
        print("[loudvox] solo estado")
        sys.stdout.flush()
        contenido = log.read_text(encoding="utf-8")
        assert "solo estado" in contenido
        assert "sesion anterior" not in contenido
    finally:
        try:
            sys.stdout.close()
        except Exception:
            pass
        sys.stdout, sys.stderr = out, err


def test_lectura_no_imprime_el_texto(tmp_path, monkeypatch, capsys):
    """El progreso de lectura va al log; el TEXTO leído no debe aparecer."""
    from loudvox_desktop import app as app_mod

    class FakePlayer:
        def play_text_chunks(self, chunks, on_chunk=None):
            for i, c in enumerate(chunks):
                on_chunk(i, c)

    obj = app_mod.DesktopApp.__new__(app_mod.DesktopApp)
    obj.player = FakePlayer()
    secreto = "Mi clave del banco es 1234 y no debe quedar en ningun log."
    obj._read(secreto)
    salida = capsys.readouterr().out
    assert "1/1" in salida            # progreso sí
    assert "clave del banco" not in salida  # contenido no


# ---------- 2) recientes desactivables + borrar ----------

@pytest.fixture
def _cfg_tmp(tmp_path, monkeypatch):
    from loudvox_desktop.viewer import recents

    monkeypatch.setattr(recents, "config_dir", lambda: tmp_path / "cfg")
    return tmp_path


def test_clear_borra_el_historial(_cfg_tmp):
    from loudvox_desktop.viewer import recents

    recents.add("/a.txt", "a.txt")
    assert recents.load()
    recents.clear()
    assert recents.load() == []
    recents.clear()  # idempotente: sin archivo tampoco falla


def test_recientes_desactivados_no_guardan_ni_muestran(_cfg_tmp):
    from loudvox_desktop.viewer import recents
    from loudvox_desktop.viewer.bridge import ViewerApi

    f = _cfg_tmp / "doc.txt"
    f.write_text("hola mundo", encoding="utf-8")

    api = ViewerApi()
    api.cfg.remember_recents = True
    api.open_path(str(f))
    assert [d["path"] for d in api.get_recents()] == [str(f)]

    api.cfg.remember_recents = False
    assert api.get_recents() == []          # no se muestran
    assert api.get_boot()["recents"] == []  # tampoco al arrancar la UI
    api.open_path(str(f))                   # y no se agregan
    api.clear_recents()
    assert recents.load() == []             # y se pueden borrar del disco


# ---------- 3) wav temporal con barrido al arrancar ----------

def test_barrido_borra_wavs_de_una_sesion_anterior(tmp_path, monkeypatch):
    import loudvox_desktop.player as pl

    monkeypatch.setattr(pl, "_TMP_DIR", tmp_path / "loudvox")
    pl._TMP_DIR.mkdir()
    restos = [pl._TMP_DIR / f"lv_{i}.wav" for i in range(3)]
    for r in restos:
        r.write_bytes(b"RIFF")
    otro = pl._TMP_DIR / "ajeno.txt"
    otro.write_text("no es wav")

    pl.AudioSink()  # al instanciar, barre los .wav huerfanos

    assert not any(r.exists() for r in restos)
    assert otro.exists()  # solo toca .wav
