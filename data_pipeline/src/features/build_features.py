"""Build ML-ready feature matrices from cleaned parquet files.

Imports ETL paths from src.etl.config when available, otherwise falls back
to a local path resolver — so this module works both on the data-etl branch
(with full ETL code) and on isolated ML branches.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from .config import (
    SINAN_SYMPTOM_COLS, SINAN_COMORBIDITY_COLS,
    SRAG_SYMPTOM_COLS, SRAG_COMORBIDITY_COLS,
    SINAN_CLASSI_FIN_TO_SEVERITY,
    DISEASE_LABELS, SEVERITY_LABELS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution — works with or without ETL module
# ---------------------------------------------------------------------------

try:
    from src.etl.config import interim_path as _etl_interim_path  # type: ignore
    def _interim_path(name: str) -> Path:
        return _etl_interim_path(name)
except ImportError:
    _PIPELINE_ROOT = Path(__file__).resolve().parents[2]
    def _interim_path(name: str) -> Path:  # type: ignore[misc]
        return _PIPELINE_ROOT / "data" / "interim" / f"{name}.parquet"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_parquet(dataset_name: str) -> pd.DataFrame | None:
    path = _interim_path(dataset_name)
    if not path.exists():
        logger.warning("Parquet not found: %s — skipping", path)
        return None
    df = pd.read_parquet(path)
    logger.info("Loaded %s: %d rows × %d cols", dataset_name, *df.shape)
    return df


def _add_temporal_features(df: pd.DataFrame, date_col: str = "DT_NOTIFIC") -> pd.DataFrame:
    out = df.copy()
    if date_col in df.columns and pd.api.types.is_datetime64_any_dtype(df[date_col]):
        out["notification_month"] = df[date_col].dt.month.astype("float32")
        out["notification_week"] = df[date_col].dt.isocalendar().week.astype("float32")
    else:
        out["notification_month"] = np.nan
        out["notification_week"] = np.nan
    return out


def _add_demographic_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Return updated df and list of added column names."""
    added = []
    if "NU_IDADE_N" in df.columns:
        df["age_years"] = df["NU_IDADE_N"].clip(0, 120).astype("float32")
        added.append("age_years")
    if "CS_SEXO" in df.columns:
        df["sex_M"] = (df["CS_SEXO"] == "M").astype("float32")
        added.append("sex_M")
    return df, added


# ---------------------------------------------------------------------------
# Disease feature builder
# ---------------------------------------------------------------------------

def build_disease_features() -> tuple[pd.DataFrame, pd.Series] | None:
    """
    Build (X, y) for disease classification.
    y labels: 0=dengue, 1=chikungunya, 2=zika, 3=influenza.
    Returns None if no parquet files are available.
    """
    sinan_sources = [
        ("sinan_dengue", 0),
        ("sinan_chikungunya", 1),
        ("sinan_zika", 2),
    ]
    pieces: list[pd.DataFrame] = []

    for ds_name, label in sinan_sources:
        df = _load_parquet(ds_name)
        if df is None:
            continue
        df = _add_temporal_features(df)
        df, demo_cols = _add_demographic_features(df)

        symptom_cols = [c for c in SINAN_SYMPTOM_COLS if c in df.columns]
        comorbidity_cols = [c for c in SINAN_COMORBIDITY_COLS if c in df.columns]
        feature_cols = symptom_cols + comorbidity_cols + [
            "notification_month", "notification_week"
        ] + demo_cols

        available = [c for c in feature_cols if c in df.columns]
        chunk = df[available].copy()
        chunk["_label"] = label
        chunk = chunk.dropna(subset=available, how="all")
        pieces.append(chunk)

    # SRAG influenza
    df_srag = _load_parquet("srag_influenza")
    if df_srag is not None:
        df_srag = _add_temporal_features(df_srag)
        df_srag, demo_cols = _add_demographic_features(df_srag)

        symptom_cols = [c for c in SRAG_SYMPTOM_COLS if c in df_srag.columns]
        comorbidity_cols = [c for c in SRAG_COMORBIDITY_COLS if c in df_srag.columns]
        feature_cols = symptom_cols + comorbidity_cols + [
            "notification_month", "notification_week"
        ] + demo_cols

        available = [c for c in feature_cols if c in df_srag.columns]
        chunk = df_srag[available].copy()
        chunk["_label"] = 3
        chunk = chunk.dropna(subset=available, how="all")
        pieces.append(chunk)

    if not pieces:
        return None

    combined = pd.concat(pieces, ignore_index=True)
    y = combined.pop("_label").astype(int)
    # Align columns: forward-fill missing columns with NaN
    X = combined
    logger.info("Disease feature matrix: %d rows × %d cols", *X.shape)
    return X, y


# ---------------------------------------------------------------------------
# Severity feature builder
# ---------------------------------------------------------------------------

def build_severity_features() -> tuple[pd.DataFrame, pd.Series] | None:
    """
    Build (X, y) for severity classification.
    y labels: 0=baixo, 1=medio, 2=alto.
    Returns None if no parquet files are available.
    """
    sinan_datasets = ["sinan_dengue", "sinan_chikungunya", "sinan_zika"]
    pieces: list[pd.DataFrame] = []

    for ds_name in sinan_datasets:
        df = _load_parquet(ds_name)
        if df is None:
            continue
        if "CLASSI_FIN" not in df.columns:
            logger.warning("%s: no CLASSI_FIN — skipping severity build", ds_name)
            continue

        df = _add_temporal_features(df)
        df, demo_cols = _add_demographic_features(df)

        df["severity"] = df["CLASSI_FIN"].map(SINAN_CLASSI_FIN_TO_SEVERITY)
        df = df.dropna(subset=["severity"])
        df["severity"] = df["severity"].astype(int)

        symptom_cols = [c for c in SINAN_SYMPTOM_COLS if c in df.columns]
        comorbidity_cols = [c for c in SINAN_COMORBIDITY_COLS if c in df.columns]
        feature_cols = symptom_cols + comorbidity_cols + [
            "notification_month", "notification_week"
        ] + demo_cols

        if "HOSPITALIZ" in df.columns:
            feature_cols.append("HOSPITALIZ")

        available = [c for c in feature_cols if c in df.columns]
        chunk = df[available + ["severity"]].dropna(subset=available, how="all")
        pieces.append(chunk)

    if not pieces:
        return None

    combined = pd.concat(pieces, ignore_index=True)
    y = combined.pop("severity").astype(int)
    X = combined
    logger.info("Severity feature matrix: %d rows × %d cols", *X.shape)
    return X, y


# ---------------------------------------------------------------------------
# Synthetic data generators (for unit tests and CI)
# ---------------------------------------------------------------------------

def make_synthetic_disease(n_per_class: int = 2_000) -> tuple[pd.DataFrame, pd.Series]:
    """Synthetic arbovirosis data with class-specific symptom signals."""
    rng = np.random.default_rng(42)
    n = n_per_class * 4

    cols = (
        SINAN_SYMPTOM_COLS
        + SINAN_COMORBIDITY_COLS
        + ["notification_month", "notification_week", "age_years", "sex_M"]
    )
    X = pd.DataFrame(
        rng.choice([0.0, 1.0], size=(n, len(cols)), p=[0.65, 0.35]).astype("float32"),
        columns=cols,
    )
    labels = np.repeat([0, 1, 2, 3], n_per_class)

    # Disease-specific signals (epidemiologically motivated)
    dengue_idx = labels == 0
    chik_idx = labels == 1
    zika_idx = labels == 2
    flu_idx = labels == 3

    X.loc[dengue_idx, "ARTRALGIA"] = rng.choice([0, 1], p=[0.25, 0.75], size=n_per_class).astype("float32")
    X.loc[dengue_idx, "PETEQUIA_N"] = rng.choice([0, 1], p=[0.4, 0.6], size=n_per_class).astype("float32")

    X.loc[chik_idx, "ARTRITE"] = rng.choice([0, 1], p=[0.10, 0.90], size=n_per_class).astype("float32")
    X.loc[chik_idx, "ARTRALGIA"] = rng.choice([0, 1], p=[0.05, 0.95], size=n_per_class).astype("float32")

    X.loc[zika_idx, "EXANTEMA"] = rng.choice([0, 1], p=[0.10, 0.90], size=n_per_class).astype("float32")
    X.loc[zika_idx, "CONJUNTVIT"] = rng.choice([0, 1], p=[0.15, 0.85], size=n_per_class).astype("float32")

    X.loc[flu_idx, "FEBRE"] = 1.0
    X.loc[flu_idx, "MIALGIA"] = rng.choice([0, 1], p=[0.2, 0.8], size=n_per_class).astype("float32")

    X["age_years"] = rng.integers(5, 80, size=n).astype("float32")
    X["sex_M"] = rng.choice([0.0, 1.0], size=n).astype("float32")
    X["notification_month"] = rng.integers(1, 13, size=n).astype("float32")
    X["notification_week"] = rng.integers(1, 53, size=n).astype("float32")

    return X, pd.Series(labels, name="_label")


def make_synthetic_severity(n_per_class: int = 2_000) -> tuple[pd.DataFrame, pd.Series]:
    """Synthetic severity data: baixo / medio / alto."""
    rng = np.random.default_rng(42)
    n = n_per_class * 3

    cols = (
        SINAN_SYMPTOM_COLS
        + SINAN_COMORBIDITY_COLS
        + ["HOSPITALIZ", "notification_month", "notification_week", "age_years", "sex_M"]
    )
    X = pd.DataFrame(
        rng.choice([0.0, 1.0], size=(n, len(cols)), p=[0.70, 0.30]).astype("float32"),
        columns=cols,
    )
    labels = np.repeat([0, 1, 2], n_per_class)

    baixo_idx = labels == 0
    medio_idx = labels == 1
    alto_idx = labels == 2

    # Alto = elderly + comorbidities + hospitalized
    X.loc[alto_idx, "age_years"] = rng.integers(60, 90, size=n_per_class).astype("float32")
    X.loc[alto_idx, ["DIABETES", "RENAL", "HEPATOPAT"]] = (
        rng.choice([0, 1], p=[0.15, 0.85], size=(n_per_class, 3)).astype("float32")
    )
    X.loc[alto_idx, "HOSPITALIZ"] = 1.0

    # Medio = some alarm signs
    X.loc[medio_idx, "PETEQUIA_N"] = rng.choice([0, 1], p=[0.3, 0.7], size=n_per_class).astype("float32")
    X.loc[medio_idx, "LACO"] = rng.choice([0, 1], p=[0.3, 0.7], size=n_per_class).astype("float32")

    # Baixo = mostly healthy, younger
    X.loc[baixo_idx, "age_years"] = rng.integers(5, 45, size=n_per_class).astype("float32")
    X.loc[baixo_idx, "HOSPITALIZ"] = 0.0

    X.loc[~alto_idx, "age_years"] = rng.integers(5, 70, size=(n - n_per_class)).astype("float32")
    X["sex_M"] = rng.choice([0.0, 1.0], size=n).astype("float32")
    X["notification_month"] = rng.integers(1, 13, size=n).astype("float32")
    X["notification_week"] = rng.integers(1, 53, size=n).astype("float32")

    return X, pd.Series(labels, name="severity")
