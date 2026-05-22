"""Cleaner para SRAG/Influenza (esquema próprio do SIVEP-Gripe).

Diferenças relevantes vs. SINAN clássico:
- Separador `;` (já em DatasetSpec).
- Tem `DT_NASC` explícito além de NU_IDADE_N → derivamos idade preferindo DT_NASC.
- Esquema com colunas próprias de UTI, antivirais, vacinação e PCR.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BaseCleaner

_VALID_SEX = {"M", "F", "I"}

_ID_COLUMNS = (
    "NU_NOTIFIC", "SG_UF_NOT", "ID_REGIONA", "CO_REGIONA", "ID_MUNICIP",
    "CO_MUN_NOT", "ID_PAIS", "CO_PAIS", "SG_UF", "ID_RG_RESI", "CO_RG_RESI",
    "ID_MN_RESI", "CO_MUN_RES", "ID_RG_INTE", "CO_RG_INTE", "ID_MN_INTE",
    "CO_MU_INTE", "NM_UN_INTE", "PAC_COCBO", "PAIS_VGM", "CO_PS_VGM",
)


class SragCleaner(BaseCleaner):
    """Limpeza específica para SRAG (influeza_srag_2025.csv)."""

    def transform_chunk(self, df: pd.DataFrame) -> pd.DataFrame:
        df = super().transform_chunk(df)

        df = self._normalize_sex(df)
        df = self._derive_age(df)
        df = self._coerce_id_columns(df)

        return df

    def _normalize_sex(self, df: pd.DataFrame) -> pd.DataFrame:
        if "CS_SEXO" not in df.columns:
            return df
        df["CS_SEXO"] = df["CS_SEXO"].str.upper()
        df.loc[~df["CS_SEXO"].isin(_VALID_SEX), "CS_SEXO"] = pd.NA
        return df

    def _derive_age(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prefere DT_NASC quando disponível; fallback para NU_IDADE_N composto."""
        anos = pd.Series(np.nan, index=df.index, dtype="float64")

        if "DT_NASC" in df.columns and "DT_NOTIFIC" in df.columns:
            delta_days = (df["DT_NOTIFIC"] - df["DT_NASC"]).dt.days
            anos = delta_days / 365.25

        if "NU_IDADE_N" in df.columns:
            idade_raw = pd.to_numeric(df["NU_IDADE_N"], errors="coerce")
            unit = (idade_raw // 1000).astype("Int64")
            value = (idade_raw % 1000).astype("Int64")
            fallback = pd.Series(np.nan, index=df.index, dtype="float64")
            fallback = fallback.mask(unit == 1, value.astype("float64") / (24 * 365.25))
            fallback = fallback.mask(unit == 2, value.astype("float64") / 365.25)
            fallback = fallback.mask(unit == 3, value.astype("float64") / 12.0)
            fallback = fallback.mask(unit == 4, value.astype("float64"))
            anos = anos.where(anos.notna(), fallback)

        anos = anos.where(anos.between(0, 130, inclusive="both"))
        df["idade_anos"] = anos
        return df

    def _coerce_id_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in _ID_COLUMNS:
            if col in df.columns:
                df[col] = df[col].astype("string")
        return df
