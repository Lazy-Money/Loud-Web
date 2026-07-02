"""Tests de configuración y hotkeys (corren 100% offline)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from loudvox.config import Config, Hotkeys, load, save, validate_hotkey


class TestHotkeys:
    def test_combinacion_valida(self):
        validate_hotkey("ctrl+alt+r")

    def test_dos_teclas_minimo_ok(self):
        validate_hotkey("ctrl+c")  # decisión del usuario, permitida

    def test_una_tecla_rechazada(self):
        with pytest.raises(ValueError, match="al menos 2 teclas"):
            validate_hotkey("f5")

    def test_tecla_vacia_rechazada(self):
        with pytest.raises(ValueError):
            validate_hotkey("ctrl+")


class TestConfigRoundtrip:
    def test_guardar_y_cargar(self, tmp_path):
        path = tmp_path / "config.json"
        cfg = Config(language="de", speed=1.5, hotkeys=Hotkeys(dictate="ctrl+shift+space"))
        save(cfg, path)
        loaded = load(path)
        assert loaded.language == "de"
        assert loaded.speed == 1.5
        assert loaded.hotkeys.dictate == "ctrl+shift+space"

    def test_defaults_sin_archivo(self, tmp_path):
        cfg = load(tmp_path / "no-existe.json")
        assert cfg.language == "es"
        assert cfg.speed == 1.0
        assert cfg.engine == "piper"

    def test_voz_por_defecto_del_idioma(self):
        assert Config(language="it").resolved_voice() == "it_IT-paola-medium"
        assert Config(language="de").resolved_voice() == "de_DE-thorsten-medium"

    def test_idioma_invalido(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text('{"language": "fr"}', encoding="utf-8")
        with pytest.raises(ValueError, match="no soportado"):
            load(path)

    def test_campo_desconocido_se_ignora(self, tmp_path):
        # Compatibilidad hacia adelante: configs de versiones futuras no rompen.
        path = tmp_path / "config.json"
        path.write_text('{"language": "en", "future_option": true}', encoding="utf-8")
        assert load(path).language == "en"


class TestVoiceOverrides:
    def test_sin_override_usa_globales(self):
        cfg = Config(speed=1.5, volume=0.8)
        p = cfg.params_for("es_ES-davefx-medium")
        assert p == {"speed": 1.5, "volume": 0.8, "speaker": None}

    def test_override_pisa_global(self):
        cfg = Config(
            speed=1.5,
            voice_overrides={"es_ES-davefx-medium": {"speed": 1.1, "volume": 0.6}},
        )
        p = cfg.params_for("es_ES-davefx-medium")
        assert p["speed"] == 1.1 and p["volume"] == 0.6

    def test_override_parcial(self):
        cfg = Config(speed=2.0, voice_overrides={"x": {"volume": 0.5}})
        p = cfg.params_for("x")
        assert p["speed"] == 2.0 and p["volume"] == 0.5

    def test_speaker_multivoz(self):
        cfg = Config(voice_overrides={"es_ES-sharvard-medium": {"speaker": 1}})
        assert cfg.params_for("es_ES-sharvard-medium")["speaker"] == 1

    def test_roundtrip_con_overrides(self, tmp_path):
        path = tmp_path / "config.json"
        save(Config(voice_overrides={"v": {"speed": 1.2}}), path)
        assert load(path).params_for("v")["speed"] == 1.2
