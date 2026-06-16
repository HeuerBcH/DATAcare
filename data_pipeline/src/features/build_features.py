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
        df["age_years"] = pd.to_numeric(df["NU_IDADE_N"], errors="coerce").clip(0, 120).astype("float32")
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

def _severity_from_outcomes(df: pd.DataFrame) -> pd.Series:
    """
    Derive severity label from clinical outcomes for diseases where CLASSI_FIN
    encodes diagnosis confirmation rather than severity (chikungunya, zika).

    Rules (applied in ascending priority):
      baixo (0): confirmed case, no alarm signs
      medio (1): hospitalized (HOSPITALIZ=True or DT_INTERNA filled)
      alto  (2): death (EVOLUCAO in {2,3} or DT_OBITO filled)
    """
    n = len(df)
    severity = pd.Series(0, index=df.index, dtype=int)

    hospitaliz = (
        df["HOSPITALIZ"].fillna(False).astype(bool)
        if "HOSPITALIZ" in df.columns
        else pd.Series(False, index=df.index)
    )
    interna = (
        df["DT_INTERNA"].notna()
        if "DT_INTERNA" in df.columns
        else pd.Series(False, index=df.index)
    )
    evolucao = (
        df["EVOLUCAO"].astype(str)
        if "EVOLUCAO" in df.columns
        else pd.Series("1", index=df.index)
    )
    obito = (
        df["DT_OBITO"].notna()
        if "DT_OBITO" in df.columns
        else pd.Series(False, index=df.index)
    )

    severity[hospitaliz | interna] = 1
    severity[evolucao.isin(["2", "3"]) | obito] = 2
    return severity


def build_severity_features() -> tuple[pd.DataFrame, pd.Series] | None:
    """
    Build (X, y) for severity classification.
    y labels: 0=baixo, 1=medio, 2=alto.

    Severity derivation per disease:
    - Dengue: CLASSI_FIN (10=baixo, 11=médio, 12=alto) — MS official scale
    - Chikungunya: outcomes-based (EVOLUCAO, HOSPITALIZ, DT_OBITO)
      CLASSI_FIN encodes confirmation (13=confirmado, 5=descartado), not severity
    - Zika: outcomes-based (EVOLUCAO, DT_OBITO)
    """
    pieces: list[pd.DataFrame] = []

    # --- Dengue: CLASSI_FIN is the official severity scale ---
    df_dengue = _load_parquet("sinan_dengue")
    if df_dengue is not None and "CLASSI_FIN" in df_dengue.columns:
        df_dengue = _add_temporal_features(df_dengue)
        df_dengue, demo_cols = _add_demographic_features(df_dengue)

        df_dengue["severity"] = (
            pd.to_numeric(df_dengue["CLASSI_FIN"], errors="coerce")
            .astype("Int64")
            .map(SINAN_CLASSI_FIN_TO_SEVERITY)
        )
        df_dengue = df_dengue.dropna(subset=["severity"])
        df_dengue["severity"] = df_dengue["severity"].astype(int)

        symptom_cols = [c for c in SINAN_SYMPTOM_COLS if c in df_dengue.columns]
        comorbidity_cols = [c for c in SINAN_COMORBIDITY_COLS if c in df_dengue.columns]
        feature_cols = symptom_cols + comorbidity_cols + [
            "notification_month", "notification_week",
        ] + demo_cols
        if "HOSPITALIZ" in df_dengue.columns:
            feature_cols.append("HOSPITALIZ")

        available = [c for c in feature_cols if c in df_dengue.columns]
        chunk = df_dengue[available + ["severity"]].dropna(subset=available, how="all")
        logger.info("Dengue severity: %d rows (baixo=%d médio=%d alto=%d)",
                    len(chunk),
                    (chunk["severity"] == 0).sum(),
                    (chunk["severity"] == 1).sum(),
                    (chunk["severity"] == 2).sum())
        pieces.append(chunk)

    # --- Chikungunya: outcomes-based severity, confirmed cases only ---
    df_chik = _load_parquet("sinan_chikungunya")
    if df_chik is not None:
        if "CLASSI_FIN" in df_chik.columns:
            df_chik = df_chik[df_chik["CLASSI_FIN"].astype(str) == "13"].copy()

        if len(df_chik) > 0:
            df_chik = _add_temporal_features(df_chik)
            df_chik, demo_cols = _add_demographic_features(df_chik)
            df_chik["severity"] = _severity_from_outcomes(df_chik)

            symptom_cols = [c for c in SINAN_SYMPTOM_COLS if c in df_chik.columns]
            comorbidity_cols = [c for c in SINAN_COMORBIDITY_COLS if c in df_chik.columns]
            feature_cols = symptom_cols + comorbidity_cols + [
                "notification_month", "notification_week",
            ] + demo_cols
            if "HOSPITALIZ" in df_chik.columns:
                feature_cols.append("HOSPITALIZ")

            available = [c for c in feature_cols if c in df_chik.columns]
            chunk = df_chik[available + ["severity"]].dropna(subset=available, how="all")
            logger.info("Chikungunya severity: %d rows (baixo=%d médio=%d alto=%d)",
                        len(chunk),
                        (chunk["severity"] == 0).sum(),
                        (chunk["severity"] == 1).sum(),
                        (chunk["severity"] == 2).sum())
            pieces.append(chunk)

    # --- Zika: outcomes-based severity, confirmed cases only ---
    df_zika = _load_parquet("sinan_zika")
    if df_zika is not None:
        if "CLASSI_FIN" in df_zika.columns:
            df_zika = df_zika[df_zika["CLASSI_FIN"].astype(str) == "2"].copy()

        if len(df_zika) > 0:
            df_zika = _add_temporal_features(df_zika)
            df_zika, demo_cols = _add_demographic_features(df_zika)
            df_zika["severity"] = _severity_from_outcomes(df_zika)

            symptom_cols = [c for c in SINAN_SYMPTOM_COLS if c in df_zika.columns]
            comorbidity_cols = [c for c in SINAN_COMORBIDITY_COLS if c in df_zika.columns]
            feature_cols = symptom_cols + comorbidity_cols + [
                "notification_month", "notification_week",
            ] + demo_cols

            available = [c for c in feature_cols if c in df_zika.columns]
            chunk = df_zika[available + ["severity"]].dropna(subset=available, how="all")
            logger.info("Zika severity: %d rows (baixo=%d médio=%d alto=%d)",
                        len(chunk),
                        (chunk["severity"] == 0).sum(),
                        (chunk["severity"] == 1).sum(),
                        (chunk["severity"] == 2).sum())
            pieces.append(chunk)

    if not pieces:
        return None

    combined = pd.concat(pieces, ignore_index=True)
    y = combined.pop("severity").astype(int)
    X = combined
    logger.info("Severity feature matrix: %d rows × %d cols — class dist: %s",
                len(X), X.shape[1], y.value_counts().to_dict())
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
