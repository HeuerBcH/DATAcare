"""Estatísticas descritivas para EDA.

Todas as funções recebem um DataFrame e retornam dicionários JSON-serializáveis,
sem efeitos colaterais (sem I/O, sem plots). O orquestrador em run_eda.py
agrega e persiste os resultados.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def basic_info(df: pd.DataFrame) -> dict[str, Any]:
    """Forma, tipos de dados e uso de memória."""
    return {
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1]),
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1_048_576, 2),
        "dtypes": df.dtypes.astype(str).to_dict(),
    }


def missing_values(df: pd.DataFrame) -> dict[str, Any]:
    """Contagem e percentual de valores ausentes por coluna."""
    missing = df.isnull().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    pct = (missing / len(df) * 100).round(2)
    return {
        "total_missing_cells": int(df.isnull().sum().sum()),
        "pct_complete_rows": round((df.dropna().shape[0] / len(df)) * 100, 2),
        "by_column": {
            col: {"count": int(missing[col]), "pct": float(pct[col])}
            for col in missing.index
        },
    }


def numeric_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Estatísticas descritivas para colunas numéricas."""
    num = df.select_dtypes(include="number")
    if num.empty:
        return {}
    desc = num.describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).T
    result: dict[str, Any] = {}
    for col, row in desc.iterrows():
        result[str(col)] = {k: _safe_float(v) for k, v in row.items()}
    return result


def categorical_summary(df: pd.DataFrame, max_categories: int = 20) -> dict[str, Any]:
    """Top-N categorias para colunas object/category."""
    cat = df.select_dtypes(include=["object", "category"])
    result: dict[str, Any] = {}
    for col in cat.columns:
        vc = df[col].value_counts(dropna=False).head(max_categories)
        result[str(col)] = {
            "n_unique": int(df[col].nunique(dropna=False)),
            "top_values": {str(k): int(v) for k, v in vc.items()},
        }
    return result


def temporal_summary(df: pd.DataFrame, date_col: str) -> dict[str, Any]:
    """Distribuição temporal: contagem de registros por mês."""
    if date_col not in df.columns:
        return {"error": f"Coluna '{date_col}' não encontrada"}

    dates = pd.to_datetime(df[date_col], errors="coerce")
    valid = dates.dropna()
    if valid.empty:
        return {"error": "Nenhuma data válida encontrada"}

    monthly = valid.dt.to_period("M").value_counts().sort_index()
    return {
        "min_date": str(valid.min().date()),
        "max_date": str(valid.max().date()),
        "span_days": int((valid.max() - valid.min()).days),
        "pct_valid_dates": round(len(valid) / len(df) * 100, 2),
        "monthly_counts": {str(k): int(v) for k, v in monthly.items()},
    }


def target_distribution(df: pd.DataFrame, target_col: str) -> dict[str, Any]:
    """Distribuição da variável alvo (CLASSI_FIN nos datasets SINAN/SRAG)."""
    if target_col not in df.columns:
        return {"error": f"Coluna '{target_col}' não encontrada"}
    vc = df[target_col].value_counts(dropna=False)
    pct = (vc / len(df) * 100).round(2)
    return {
        "n_unique": int(df[target_col].nunique(dropna=False)),
        "distribution": {
            str(k): {"count": int(vc[k]), "pct": float(pct[k])}
            for k in vc.index
        },
    }


def geographic_summary(df: pd.DataFrame, ibge_col: str, top_n: int = 20) -> dict[str, Any]:
    """Top municípios por volume de registros."""
    if ibge_col not in df.columns:
        return {"error": f"Coluna '{ibge_col}' não encontrada"}
    vc = df[ibge_col].value_counts().head(top_n)
    return {
        "n_unique_municipios": int(df[ibge_col].nunique()),
        "top_municipios": {str(k): int(v) for k, v in vc.items()},
    }


def duplicate_analysis(df: pd.DataFrame) -> dict[str, Any]:
    """Linhas completamente duplicadas."""
    n_dup = int(df.duplicated().sum())
    return {
        "n_duplicates": n_dup,
        "pct_duplicates": round(n_dup / len(df) * 100, 2),
    }


# ─────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────

def _safe_float(v: Any) -> float | None:
    try:
        f = float(v)
        return None if (np.isnan(f) or np.isinf(f)) else round(f, 4)
    except (TypeError, ValueError):
        return None
