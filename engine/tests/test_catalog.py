import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loudvox.catalog import list_catalog


def fake_voice(dir, voice_id, locale, dataset, speakers=None):
    (dir / f"{voice_id}.onnx").write_bytes(b"fake")
    meta = {"language": {"code": locale}, "dataset": dataset,
            "num_speakers": len(speakers) if speakers else 1}
    if speakers:
        meta["speaker_id_map"] = speakers
    (dir / f"{voice_id}.onnx.json").write_text(json.dumps(meta), encoding="utf-8")


def test_voz_simple_con_genero(tmp_path):
    fake_voice(tmp_path, "es_ES-davefx-medium", "es_ES", "davefx")
    (entry,) = list_catalog(tmp_path)
    assert entry["lang"] == "es" and entry["region"] == "España"
    assert entry["gender"] == "M" and entry["speaker"] is None
    assert entry["label"] == "España — Davefx (masculino)"


def test_multi_hablante_expande_en_dos(tmp_path):
    fake_voice(tmp_path, "es_ES-sharvard-medium", "es_ES", "sharvard",
               speakers={"F": 0, "M": 1})
    entries = list_catalog(tmp_path)
    assert len(entries) == 2
    f, m = entries
    assert f["speaker"] == 0 and f["gender"] == "F" and "femenino" in f["label"]
    assert m["speaker"] == 1 and m["gender"] == "M" and "masculino" in m["label"]
    assert f["id"] == m["id"] == "es_ES-sharvard-medium"


def test_region_mexico(tmp_path):
    fake_voice(tmp_path, "es_MX-claude-high", "es_MX", "claude")
    (entry,) = list_catalog(tmp_path)
    assert entry["region"] == "México" and entry["lang"] == "es"
    assert entry["label"] == "México — Claude (femenino)"  # confirmado a oído


def test_kokoro_solo_si_modelo_instalado(tmp_path):
    assert all(e["engine"] == "piper" for e in list_catalog(tmp_path))
    (tmp_path / "kokoro-v1.0.onnx").write_bytes(b"fake")
    (tmp_path / "voices-v1.0.bin").write_bytes(b"fake")
    entries = list_catalog(tmp_path)
    kokoro = [e for e in entries if e["engine"] == "kokoro"]
    assert any(e["id"] == "ef_dora" and e["gender"] == "F" for e in kokoro)
    assert any(e["id"] == "em_alex" and e["region"] == "España" for e in kokoro)


def test_dir_inexistente(tmp_path):
    assert list_catalog(tmp_path / "nada") == []
