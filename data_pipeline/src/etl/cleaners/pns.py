"""Cleaner para PNS 2019 (Pesquisa Nacional de Saúde — microdados IBGE).

Particularidades:
- Survey clusterizado: `UPA_PNS` é a unidade primária de amostragem (PSU). Em
  qualquer split, todos os respondentes de uma UPA devem permanecer juntos.
- Variáveis codificadas: V0001=UF, V0024=município, A001=situação censitária...
- Pesos amostrais não são features — sinalizados para uso posterior em análise.
- `UPA_PNS` e `V0024` são códigos numéricos longos — mantidos como string.
"""

from __future__ import annotations

import pandas as pd

from .base import BaseCleaner

# Variáveis de identificação / desenho amostral. Devem ser string para preservar zeros.
_DESIGN_ID_COLS = (
    "V0001", "V0024", "UPA_PNS", "V0006_PNS", "V0015", "V0020", "V0022",
    "V0026", "V0031",
)

# Possíveis colunas de pesos amostrais (varia entre versões dos microdados).
_WEIGHT_COLS_CANDIDATES = ("V0028", "V0029", "V00291", "V00292", "V00293")


class PnsCleaner(BaseCleaner):
    """Limpeza específica para PNS 2019."""

    def transform_chunk(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._strip_strings(df)
        df = self._coerce_design_columns(df)
        df = self._coerce_weights(df)
        df = self._drop_exact_duplicates(df)
        return df

    def _coerce_design_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in _DESIGN_ID_COLS:
            if col in df.columns:
                df[col] = df[col].astype("string")
        return df

    def _coerce_weights(self, df: pd.DataFrame) -> pd.DataFrame:
        present = [c for c in _WEIGHT_COLS_CANDIDATES if c in df.columns]
        for col in present:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        if present:
            note = f"colunas de peso detectadas e convertidas: {present}"
            if note not in self.report.notes:
                self.report.notes.append(note)
        return df
