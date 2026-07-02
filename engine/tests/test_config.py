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
