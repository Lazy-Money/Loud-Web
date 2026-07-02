"""Tests del normalizador de abreviaturas (corren 100% offline)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from loudvox.normalizer import Entry, Normalizer, parse_csv, BUNDLED_DIR


def norm(lang):
    return Normalizer.for_language(lang)


class TestUnits:
    def test_plural_basico(self):
        assert norm("es").normalize("Corrió 10 m") == "Corrió 10 metros"

    def test_singular(self):
        assert norm("es").normalize("Mide 1 m") == "Mide 1 metro"

    def test_decimal_es_plural(self):
        assert norm("es").normalize("Mide 1,8 m") == "Mide 1,8 metros"

    def test_sin_espacio(self):
        assert norm("es").normalize("Faltan 10m") == "Faltan 10 metros"

    def test_km_gana_a_m(self):
        assert norm("es").normalize("Son 5 km") == "Son 5 kilómetros"

    def test_m_suelta_no_se_toca(self):
        assert norm("es").normalize("La letra m es linda") == "La letra m es linda"

    def test_unidad_dentro_de_palabra_no_se_toca(self):
        # "10 metros" ya expandido no debe volver a tocarse
        assert norm("es").normalize("10 metros") == "10 metros"
        assert norm("es").normalize("10 min de video") == "10 minutos de video"

    def test_porcentaje(self):
        assert norm("es").normalize("El 25 % restante") == "El 25 por ciento restante"

    def test_compuesta_km_h(self):
        assert norm("es").normalize("A 120 km/h") == "A 120 kilómetros por hora"

    def test_ingles(self):
        assert norm("en").normalize("Run 5 km now") == "Run 5 kilometers now"
        assert norm("en").normalize("Just 1 km") == "Just 1 kilometer"

    def test_italiano(self):
        assert norm("it").normalize("Sono 10 km") == "Sono 10 chilometri"

    def test_aleman(self):
        assert norm("de").normalize("Noch 10 km") == "Noch 10 Kilometer"


class TestWords:
    def test_doctor(self):
        assert norm("es").normalize("El Dr. García llegó") == "El Doctor García llegó"

    def test_etcetera(self):
        assert norm("es").normalize("frutas, verduras, etc.") == "frutas, verduras, etcétera"

    def test_no_dentro_de_palabra(self):
        # "arte." no debe activar "art."
        assert norm("es").normalize("Me gusta el arte.") == "Me gusta el arte."

    def test_ingles_mr(self):
        assert norm("en").normalize("Mr. Smith called") == "Mister Smith called"

    def test_aleman_zb(self):
        assert norm("de").normalize("Obst, z.B. Äpfel") == "Obst, zum Beispiel Äpfel"


class TestUserOverride:
    def test_diccionario_usuario_tiene_prioridad(self, tmp_path):
        user_csv = tmp_path / "custom.csv"
        user_csv.write_text("m,minuto,minutos,unit\n", encoding="utf-8")
        n = Normalizer.for_language("es", extra_paths=[user_csv])
        assert n.normalize("10 m") == "10 minutos"

    def test_entrada_nueva_del_usuario(self, tmp_path):
        user_csv = tmp_path / "custom.csv"
        user_csv.write_text("GHz,gigahercio,gigahercios,unit\n", encoding="utf-8")
        n = Normalizer.for_language("es", extra_paths=[user_csv])
        assert n.normalize("3 GHz") == "3 gigahercios"


class TestCSVParsing:
    def test_todos_los_idiomas_parsean(self):
        for lang in ("es", "en", "it", "de"):
            entries = parse_csv(BUNDLED_DIR / f"{lang}.csv")
            assert len(entries) > 10, f"{lang}: diccionario sospechosamente corto"

    def test_fila_invalida(self, tmp_path):
        bad = tmp_path / "bad.csv"
        bad.write_text("m,metro\n", encoding="utf-8")
        with pytest.raises(ValueError, match="4 columnas"):
            parse_csv(bad)

    def test_modo_invalido(self, tmp_path):
        bad = tmp_path / "bad.csv"
        bad.write_text("m,metro,metros,banana\n", encoding="utf-8")
        with pytest.raises(ValueError, match="modo desconocido"):
            parse_csv(bad)
