"""Cleaner para `taxa_incid_*` (indicadores agregados por município × mês).

São dados públicos com granularidade municipal e competência mensal
(`co_anomes` em formato AAAAMM). Limpeza é mais leve: tipagem dos
indicadores numéricos e normalização da data de competência.
"""

from __future__ import annotations

import pandas as pd

from .base import BaseCleaner

_NUMERIC_COLS = (
    "vl_indicador_calculado_mun",
    "vl_indicador_calculado_rs",
    "vl_indicador_calculado_ms",
    "vl_indicador_calculado_uf",
    "vl_indicador_calculado_reg",
    "vl_indicador_calculado_br",
    "vl_indicador_calculado_al",
)

_ID_COLS = (
    "co_anomes", "co_ibge", "co_uf", "co_regiao_brasil",
    "co_regiao_saude", "co_macro", "co_item_categoria",
)


class TaxaIncidCleaner(BaseCleaner):
    """Limpeza para `taxa_incid_dengue.csv`, `taxa_incid_zika.csv`, `taxa_indic_chikungunya.csv`."""

    def transform_chunk(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._strip_strings(df)
        df = self._cast_ids(df)
        df = self._cast_numerics(df)
        df = self._parse_competencia(df)
        df = self._drop_exact_duplicates(df)
        return df

    def _cast_ids(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in _ID_COLS:
            if col in df.columns:
                df[col] = df[col].astype("string")
        return df

    def _cast_numerics(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in _NUMERIC_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def _parse_competencia(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza `dt_competencia` (data) e mantém `co_anomes` para split temporal."""
        if "dt_competencia" in df.columns:
            df["dt_competencia"] = pd.to_datetime(
                df["dt_competencia"], errors="coerce", dayfirst=True
            )
            if "dt_competencia" not in self.report.date_columns_parsed:
                self.report.date_columns_parsed.append("dt_competencia")
        if "dt_atualizacao" in df.columns:
            # Timestamp do sistema, sempre em ISO — sem dayfirst.
            df["dt_atualizacao"] = pd.to_datetime(
                df["dt_atualizacao"], errors="coerce"
            )
        return df
