"""Cleaner para SINAN clássico (dengue, chikungunya, zika).

Particularidades tratadas:
- `NU_IDADE_N` codifica idade em forma composta (TP_IDADE+valor) — derivamos `idade_anos`.
- `CS_SEXO` chega como M/F/I; normalizado para uppercase, valores fora desse set → NaN.
- `CLASSI_FIN` (classificação final) tem códigos por agravo; mantemos como categórico.
- IDs (`ID_MUNICIP`, `ID_REGIONA`, etc.) são códigos IBGE — mantidos como string para preservar zeros à esquerda.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import BaseCleaner

_VALID_SEX = {"M", "F", "I"}

# Códigos IBGE / categóricos que NÃO devem virar numéricos.
_ID_COLUMNS = (
    "TP_NOT", "ID_AGRAVO", "SG_UF_NOT", "ID_MUNICIP", "ID_REGIONA",
    "ID_UNIDADE", "SG_UF", "ID_MN_RESI", "ID_RG_RESI", "ID_PAIS",
    "ID_OCUPA_N", "COUFINF", "COPAISINF", "COMUNINF", "MUNICIPIO", "UF",
)


class SinanCleaner(BaseCleaner):
    """Limpeza específica para SINAN dengue/chik/zika."""

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
        """Deriva `idade_anos` a partir de NU_IDADE_N (padrão SINAN).

        Convenção SINAN: NU_IDADE_N é um número de 4 dígitos onde o primeiro
        dígito indica a unidade (1=hora, 2=dia, 3=mês, 4=ano) e os 3 últimos
        o valor. Ex.: 4023 = 23 anos; 3006 = 6 meses; 2014 = 14 dias.

        Quando a coluna não existe ou está vazia, deixa NaN.
        """
        if "NU_IDADE_N" not in df.columns:
            return df

        idade_raw = pd.to_numeric(df["NU_IDADE_N"], errors="coerce")
        unit = (idade_raw // 1000).astype("Int64")
        value = (idade_raw % 1000).astype("Int64")

        # 1=hora, 2=dia, 3=mês, 4=ano
        anos = pd.Series(np.nan, index=df.index, dtype="float64")
        anos = anos.mask(unit == 1, value.astype("float64") / (24 * 365.25))
        anos = anos.mask(unit == 2, value.astype("float64") / 365.25)
        anos = anos.mask(unit == 3, value.astype("float64") / 12.0)
        anos = anos.mask(unit == 4, value.astype("float64"))

        # Idades acima de 130 anos = código inválido → NaN.
        anos = anos.where(anos.between(0, 130, inclusive="both"))

        df["idade_anos"] = anos
        return df

    def _coerce_id_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mantém IDs como string para preservar zeros à esquerda."""
        for col in _ID_COLUMNS:
            if col in df.columns:
                df[col] = df[col].astype("string")
        return df
