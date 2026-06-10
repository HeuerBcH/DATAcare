"""Testes dos cleaners — focados nas regras com semântica de domínio:
- decodificação composta de idade (SINAN/SRAG)
- recode 1/2/9 → boolean
- preservação de zeros à esquerda em IDs
- normalização de sexo
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.etl.cleaners.base import BaseCleaner  # noqa: E402
from src.etl.cleaners.sinan import SinanCleaner  # noqa: E402
from src.etl.cleaners.srag import SragCleaner  # noqa: E402
from src.etl.cleaners.taxa_incid import TaxaIncidCleaner  # noqa: E402
from src.etl.config import DATASETS  # noqa: E402


# ---------------------------------------------------------------------------
# SINAN
# ---------------------------------------------------------------------------

class TestSinanCleaner:
    def _cleaner(self) -> SinanCleaner:
        return SinanCleaner(DATASETS["sinan_dengue"])

    def test_age_decoding_years(self):
        df = pd.DataFrame({"NU_IDADE_N": ["4023", "4001", "4130"]})
        out = self._cleaner().transform_chunk(df)
        assert out["idade_anos"].iloc[0] == 23
        assert out["idade_anos"].iloc[1] == 1
        # 130 ainda é válido (limite inclusivo); 131+ vira NaN.
        assert out["idade_anos"].iloc[2] == 130

    def test_age_decoding_months_days_hours(self):
        df = pd.DataFrame({"NU_IDADE_N": ["3006", "2014", "1012"]})
        out = self._cleaner().transform_chunk(df)
        assert out["idade_anos"].iloc[0] == pytest.approx(0.5, abs=0.05)
        assert out["idade_anos"].iloc[1] == pytest.approx(14 / 365.25, abs=0.005)
        assert out["idade_anos"].iloc[2] < 0.01

    def test_age_invalid_becomes_nan(self):
        df = pd.DataFrame({"NU_IDADE_N": ["9999", "ABC", "4500"]})
        out = self._cleaner().transform_chunk(df)
        # 9999 → unidade 9 inválida (sem mask), fica NaN
        # ABC → coerce vira NaN
        # 4500 → 500 anos > 130, vira NaN
        assert out["idade_anos"].isna().sum() == 3

    def test_yes_no_recoded_to_boolean(self):
        df = pd.DataFrame({
            "FEBRE":   ["1", "2", "9", None],
            "DIABETES": ["1", "1", "2", "9"],
        })
        out = self._cleaner().transform_chunk(df)
        assert list(out["FEBRE"]) == [True, False, pd.NA, pd.NA]
        assert out["FEBRE"].dtype == "boolean"
        assert list(out["DIABETES"]) == [True, True, False, pd.NA]

    def test_sex_normalization(self):
        df = pd.DataFrame({"CS_SEXO": ["m", "F", "X", "i", " "]})
        out = self._cleaner().transform_chunk(df)
        assert out["CS_SEXO"].iloc[0] == "M"
        assert out["CS_SEXO"].iloc[1] == "F"
        assert pd.isna(out["CS_SEXO"].iloc[2])
        assert out["CS_SEXO"].iloc[3] == "I"

    def test_id_columns_stay_as_string(self):
        df = pd.DataFrame({
            "ID_MUNICIP": ["355030", "330455"],
            "SG_UF_NOT":   ["35", "33"],
        })
        out = self._cleaner().transform_chunk(df)
        assert out["ID_MUNICIP"].dtype == "string"
        assert out["ID_MUNICIP"].iloc[0] == "355030"

    def test_duplicates_dropped(self):
        df = pd.DataFrame({
            "NU_IDADE_N": ["4030", "4030", "4031"],
            "CS_SEXO":    ["M", "M", "F"],
        })
        cleaner = self._cleaner()
        out = cleaner.transform_chunk(df)
        assert len(out) == 2
        assert cleaner.report.duplicates_dropped == 1


# ---------------------------------------------------------------------------
# SRAG
# ---------------------------------------------------------------------------

class TestSragCleaner:
    def test_age_prefers_dt_nasc(self):
        df = pd.DataFrame({
            "DT_NASC":    ["1990-01-01", "2000-06-15"],
            "DT_NOTIFIC": ["2024-01-01", "2024-01-01"],
            "NU_IDADE_N": ["4034", "9999"],
        })
        cleaner = SragCleaner(DATASETS["srag_influenza"])
        out = cleaner.transform_chunk(df)
        # Deve usar DT_NASC, não NU_IDADE_N.
        assert out["idade_anos"].iloc[0] == pytest.approx(34, abs=0.5)
        assert out["idade_anos"].iloc[1] == pytest.approx(23.6, abs=0.5)

    def test_age_falls_back_to_nu_idade_when_dt_nasc_missing(self):
        df = pd.DataFrame({
            "DT_NASC":    [None, None],
            "DT_NOTIFIC": ["2024-01-01", "2024-01-01"],
            "NU_IDADE_N": ["4023", "4045"],
        })
        cleaner = SragCleaner(DATASETS["srag_influenza"])
        out = cleaner.transform_chunk(df)
        assert out["idade_anos"].iloc[0] == 23
        assert out["idade_anos"].iloc[1] == 45


# ---------------------------------------------------------------------------
# Taxa incid
# ---------------------------------------------------------------------------

class TestTaxaIncidCleaner:
    def test_numeric_columns_are_cast(self):
        df = pd.DataFrame({
            "co_anomes": ["202401", "202402"],
            "vl_indicador_calculado_mun": ["12.3", "45.6"],
            "vl_indicador_calculado_uf":  ["7.8", "9.1"],
        })
        cleaner = TaxaIncidCleaner(DATASETS["taxa_incid_dengue"])
        out = cleaner.transform_chunk(df)
        assert pd.api.types.is_numeric_dtype(out["vl_indicador_calculado_mun"])
        assert out["vl_indicador_calculado_mun"].iloc[0] == 12.3

    def test_ids_preserve_string_zeros(self):
        df = pd.DataFrame({
            "co_anomes": ["202401"],
            "co_ibge":   ["3550308"],
        })
        cleaner = TaxaIncidCleaner(DATASETS["taxa_incid_dengue"])
        out = cleaner.transform_chunk(df)
        assert out["co_ibge"].dtype == "string"
        assert out["co_ibge"].iloc[0] == "3550308"


# ---------------------------------------------------------------------------
# Fixes da revisão de código
# ---------------------------------------------------------------------------

class TestDateParseBrazilianFormat:
    """#2: _parse_dates precisa recuperar DD/MM/AAAA preservando a string original."""

    def test_mixed_iso_and_brazilian_dates_both_recovered(self):
        from dataclasses import replace
        spec = replace(DATASETS["sinan_dengue"], date_columns=("DT_NOTIFIC",))
        cleaner = SinanCleaner(spec)
        df = pd.DataFrame({"DT_NOTIFIC": [
            "2024-01-15", "15/03/2024", "2024-02-20", "20/04/2024"
        ]})
        out = cleaner.transform_chunk(df)
        # Antes do fix, as 2 datas em DD/MM/AAAA viravam NaT.
        assert out["DT_NOTIFIC"].notna().sum() == 4, (
            f"Esperava 4 datas válidas, ficou: {list(out['DT_NOTIFIC'])}"
        )
        assert out["DT_NOTIFIC"].iloc[1] == pd.Timestamp("2024-03-15")
        assert out["DT_NOTIFIC"].iloc[3] == pd.Timestamp("2024-04-20")


class TestSentinelReplacement:
    """#7: _replace_sentinels precisa ser de fato chamado quando declarado no DatasetSpec."""

    def test_numeric_sentinels_become_nan(self):
        from dataclasses import replace
        spec = replace(
            DATASETS["sinan_dengue"],
            numeric_sentinel_columns=("DOSE_VAC",),
            sentinels=(99, 999),
        )
        cleaner = SinanCleaner(spec)
        # Inclui coluna _id para impedir que `drop_duplicates` colapse
        # as duas linhas que ficam com NaN após o replace.
        df = pd.DataFrame({
            "DOSE_VAC": ["1", "2", "99", "3", "999"],
            "_id":      ["a", "b", "c", "d", "e"],
        })
        out = cleaner.transform_chunk(df).sort_values("_id").reset_index(drop=True)
        numeric = pd.to_numeric(out["DOSE_VAC"], errors="coerce")
        assert numeric.iloc[0] == 1
        assert numeric.iloc[1] == 2
        assert pd.isna(numeric.iloc[2]), "99 deveria ter virado NaN"
        assert numeric.iloc[3] == 3
        assert pd.isna(numeric.iloc[4]), "999 deveria ter virado NaN"


class TestCleanManyReturnsFailures:
    """#1: clean_many devolve lista de falhas em vez de chamar sys.exit."""

    def test_returns_failures_list_when_file_missing(self, tmp_path, monkeypatch):
        import src.etl.config as cfg
        import src.etl.clean as clean_mod
        from dataclasses import replace

        # Aponta RAW_DATA_DIR para tmp_path vazio para forçar FileNotFoundError.
        monkeypatch.setattr(cfg, "RAW_DATA_DIR", tmp_path)
        monkeypatch.setattr(clean_mod, "DATASETS", cfg.DATASETS)
        # Usa um dataset que precisa de arquivo bruto.
        spec = replace(DATASETS["sinan_zika"], filename="arquivo_inexistente.csv")
        result = clean_mod.clean_many([spec])
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0][0] == spec.name
        assert "FileNotFoundError" in result[0][1] or "não encontrado" in result[0][1]

    def test_returns_empty_list_on_success_dry_run(self, tmp_path):
        """Sem datasets para limpar → lista vazia, sem sys.exit."""
        from src.etl.clean import clean_many
        result = clean_many([])
        assert result == []
