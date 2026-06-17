"""Camada de acesso a dados do dashboard DATAcare.

Lê de forma robusta os artefatos gerados pelo pipeline (relatórios de ETL,
relatórios de ML, parquets limpos e modelos MLflow). Tudo é tolerante a
arquivos ausentes — se um artefato ainda não foi gerado, o loader retorna
estrutura vazia em vez de quebrar a aplicação.

Allowlist de datasets
---------------------
Apenas os 4 datasets ativos do projeto (``sinan_*`` e ``srag_influenza``)
são expostos ao dashboard. Parquets remanescentes de CSVs que saíram do
projeto (``pns_2019``, ``taxa_incid_*``) são silenciosamente ignorados.
A fonte da verdade é ``src.etl.config.DATASETS``.
"""
from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import streamlit as st

# ---------------------------------------------------------------------------
# Resolução de caminhos
# ---------------------------------------------------------------------------

# dashboard/ -> data_pipeline/
_DEFAULT_PIPELINE_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = Path(os.environ.get("DATACARE_PIPELINE_DIR", str(_DEFAULT_PIPELINE_ROOT)))

DATA_DIR = PIPELINE_ROOT / "data"
REPORTS_DIR = DATA_DIR / "reports"
CLEANING_DIR = REPORTS_DIR / "cleaning"
LEAKAGE_DIR = REPORTS_DIR / "leakage"
ML_DIR = REPORTS_DIR / "ml"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = PIPELINE_ROOT / "models"

# ---------------------------------------------------------------------------
# Allowlist e metadados de apresentação
# ---------------------------------------------------------------------------

# Datasets ativos do projeto. Qualquer parquet/relatório fora desta lista é
# considerado órfão de uma rodada antiga (CSV já removido) e fica fora do
# dashboard para não confundir o usuário.
VALID_DATASETS: tuple[str, ...] = (
    "sinan_dengue",
    "sinan_chikungunya",
    "sinan_zika",
    "srag_influenza",
)

DATASET_LABELS: dict[str, str] = {
    "sinan_dengue": "Dengue (SINAN)",
    "sinan_chikungunya": "Chikungunya (SINAN)",
    "sinan_zika": "Zika (SINAN)",
    "srag_influenza": "Influenza (SRAG)",
}

# Datasets que alimentam diretamente os modelos de classificação.
MODEL_DATASETS = list(VALID_DATASETS)

DISEASE_REPORT = "disease_classifier"
SEVERITY_REPORT = "severity_classifier"


def is_valid_dataset(name: str) -> bool:
    return name in VALID_DATASETS


def pretty_dataset(name: str) -> str:
    return DATASET_LABELS.get(name, name.replace("_", " ").title())


# ---------------------------------------------------------------------------
# Helpers de leitura
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _dir_signature(folder: Path) -> tuple:
    """Assinatura (nome, mtime) dos JSONs válidos de uma pasta."""
    if not folder.exists():
        return ()
    return tuple(
        sorted(
            (p.name, p.stat().st_mtime)
            for p in folder.glob("*.json")
            if p.stem in VALID_DATASETS or p.stem.endswith("_report")
        )
    )


# ---------------------------------------------------------------------------
# Relatórios de limpeza (ETL)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_cleaning_reports(_sig: tuple) -> pd.DataFrame:
    rows: list[dict] = []
    if CLEANING_DIR.exists():
        for path in sorted(CLEANING_DIR.glob("*.json")):
            if path.stem not in VALID_DATASETS:
                continue
            data = _read_json(path)
            if not data:
                continue
            raw = data.get("raw_rows") or 0
            cleaned = data.get("cleaned_rows") or 0
            rows.append(
                {
                    "dataset": data.get("dataset", path.stem),
                    "label": pretty_dataset(data.get("dataset", path.stem)),
                    "source_file": data.get("source_file", "—"),
                    "raw_rows": raw,
                    "cleaned_rows": cleaned,
                    "rows_removed": max(raw - cleaned, 0),
                    "retention_pct": round(100 * cleaned / raw, 2) if raw else 0.0,
                    "duplicates_dropped": data.get("duplicates_dropped", 0),
                    "rows_with_invalid_dates": data.get("rows_with_invalid_dates", 0),
                    "n_yes_no_recoded": len(data.get("yes_no_columns_recoded", []) or []),
                    "n_date_cols_parsed": len(data.get("date_columns_parsed", []) or []),
                    "n_cols_dropped": len(data.get("columns_dropped_all_null", []) or []),
                    "notes": "; ".join(data.get("notes", []) or []),
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Relatórios de leakage / split (ETL)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_leakage_reports(_sig: tuple) -> pd.DataFrame:
    rows: list[dict] = []
    if LEAKAGE_DIR.exists():
        for path in sorted(LEAKAGE_DIR.glob("*.json")):
            if path.stem not in VALID_DATASETS:
                continue
            data = _read_json(path)
            if not data:
                continue
            sizes = data.get("sizes", {}) or {}
            overlaps = data.get("group_overlaps", {}) or {}
            rows.append(
                {
                    "dataset": data.get("dataset", path.stem),
                    "label": pretty_dataset(data.get("dataset", path.stem)),
                    "strategy": data.get("strategy", "—"),
                    "train": sizes.get("train", 0),
                    "val": sizes.get("val", 0),
                    "test": sizes.get("test", 0),
                    "total": sum(sizes.values()) if sizes else 0,
                    "temporal_order_ok": bool(data.get("temporal_order_ok", False)),
                    "duplicate_rows_across_splits": data.get(
                        "duplicate_rows_across_splits", 0
                    ),
                    "n_group_overlaps": len(overlaps),
                    "n_errors": len(data.get("errors", []) or []),
                    "n_warnings": len(data.get("warnings", []) or []),
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Relatórios de ML
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_ml_report(name: str, _sig: tuple) -> dict | None:
    return _read_json(ML_DIR / f"{name}_report.json")


def cleaning_signature() -> tuple:
    return _dir_signature(CLEANING_DIR)


def leakage_signature() -> tuple:
    return _dir_signature(LEAKAGE_DIR)


def ml_signature() -> tuple:
    return _dir_signature(ML_DIR)


# ---------------------------------------------------------------------------
# Parquets limpos (exploração de dados)
# ---------------------------------------------------------------------------

def list_interim_datasets() -> list[str]:
    """Lista apenas os parquets dos datasets válidos."""
    if not INTERIM_DIR.exists():
        return []
    found = {p.stem for p in INTERIM_DIR.glob("*.parquet")}
    return [name for name in VALID_DATASETS if name in found]


def interim_path(dataset: str) -> Path:
    return INTERIM_DIR / f"{dataset}.parquet"


@st.cache_data(show_spinner=False)
def parquet_schema(path_str: str, _mtime: float) -> list[str]:
    try:
        return list(pq.ParquetFile(path_str).schema.names)
    except Exception:
        return []


@st.cache_data(show_spinner=False)
def parquet_num_rows(path_str: str, _mtime: float) -> int:
    try:
        return pq.ParquetFile(path_str).metadata.num_rows
    except Exception:
        return 0


@st.cache_data(show_spinner=True)
def load_columns(path_str: str, columns: tuple[str, ...], sample_n: int, _mtime: float) -> pd.DataFrame:
    """Lê apenas as colunas pedidas (eficiente) e amostra se necessário."""
    if not columns:
        return pd.DataFrame()
    try:
        df = pd.read_parquet(path_str, columns=list(columns))
    except Exception:
        return pd.DataFrame()
    if sample_n and len(df) > sample_n:
        df = df.sample(sample_n, random_state=42)
    return df


def file_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


# ---------------------------------------------------------------------------
# Detecção semântica de colunas (robusta entre SINAN e SRAG)
# ---------------------------------------------------------------------------

def detect_age_column(columns: list[str]) -> str | None:
    for cand in ("idade_anos", "age_years", "NU_IDADE_N"):
        if cand in columns:
            return cand
    return None


def detect_date_column(columns: list[str]) -> str | None:
    for cand in ("DT_NOTIFIC", "DT_SIN_PRI"):
        if cand in columns:
            return cand
    return None


def detect_sex_column(columns: list[str]) -> str | None:
    return "CS_SEXO" if "CS_SEXO" in columns else None


def detect_class_column(columns: list[str]) -> str | None:
    return "CLASSI_FIN" if "CLASSI_FIN" in columns else None


# ---------------------------------------------------------------------------
# Metadados de features (para o preditor interativo)
# ---------------------------------------------------------------------------

# Nome humano + grupo para cada feature de entrada dos modelos. Usado tanto
# pela página de previsão (formulário agrupado) quanto pelos detalhes de
# importância para renderizar rótulos legíveis.
FEATURE_META: dict[str, dict[str, str]] = {
    # Sintomas SINAN (arboviroses)
    "FEBRE":       {"label": "Febre",                  "group": "Sintomas",       "kind": "bool"},
    "MIALGIA":     {"label": "Mialgia (dor muscular)", "group": "Sintomas",       "kind": "bool"},
    "CEFALEIA":    {"label": "Cefaleia",               "group": "Sintomas",       "kind": "bool"},
    "EXANTEMA":    {"label": "Exantema (manchas)",     "group": "Sintomas",       "kind": "bool"},
    "VOMITO":      {"label": "Vômito",                 "group": "Sintomas",       "kind": "bool"},
    "NAUSEA":      {"label": "Náusea",                 "group": "Sintomas",       "kind": "bool"},
    "DOR_COSTAS":  {"label": "Dor nas costas",         "group": "Sintomas",       "kind": "bool"},
    "CONJUNTVIT":  {"label": "Conjuntivite",           "group": "Sintomas",       "kind": "bool"},
    "ARTRITE":     {"label": "Artrite",                "group": "Sintomas",       "kind": "bool"},
    "ARTRALGIA":   {"label": "Artralgia (dor articular)", "group": "Sintomas",    "kind": "bool"},
    "PETEQUIA_N":  {"label": "Petéquias",              "group": "Sintomas",       "kind": "bool"},
    "LEUCOPENIA":  {"label": "Leucopenia",             "group": "Sintomas",       "kind": "bool"},
    "LACO":        {"label": "Prova do laço",          "group": "Sintomas",       "kind": "bool"},
    "DOR_RETRO":   {"label": "Dor retro-orbital",      "group": "Sintomas",       "kind": "bool"},
    # Sintomas SRAG (respiratórios)
    "TOSSE":       {"label": "Tosse",                  "group": "Sintomas resp.", "kind": "bool"},
    "GARGANTA":    {"label": "Dor de garganta",        "group": "Sintomas resp.", "kind": "bool"},
    "DISPNEIA":    {"label": "Dispneia",               "group": "Sintomas resp.", "kind": "bool"},
    "DESC_RESP":   {"label": "Desconforto respiratório", "group": "Sintomas resp.", "kind": "bool"},
    "DIARREIA":    {"label": "Diarreia",               "group": "Sintomas resp.", "kind": "bool"},
    "FADIGA":      {"label": "Fadiga",                 "group": "Sintomas resp.", "kind": "bool"},
    # Comorbidades
    "DIABETES":    {"label": "Diabetes",               "group": "Comorbidades",   "kind": "bool"},
    "HEMATOLOG":   {"label": "Doença hematológica",    "group": "Comorbidades",   "kind": "bool"},
    "HEPATOPAT":   {"label": "Hepatopatia",            "group": "Comorbidades",   "kind": "bool"},
    "RENAL":       {"label": "Doença renal",           "group": "Comorbidades",   "kind": "bool"},
    "HIPERTENSA":  {"label": "Hipertensão",            "group": "Comorbidades",   "kind": "bool"},
    "ACIDO_PEPT":  {"label": "Doença ácido-péptica",   "group": "Comorbidades",   "kind": "bool"},
    "AUTO_IMUNE":  {"label": "Doença auto-imune",      "group": "Comorbidades",   "kind": "bool"},
    "CARDIOPATI":  {"label": "Cardiopatia",            "group": "Comorbidades",   "kind": "bool"},
    "NEUROLOGIC":  {"label": "Doença neurológica",     "group": "Comorbidades",   "kind": "bool"},
    "PNEUMOPATI":  {"label": "Pneumopatia",            "group": "Comorbidades",   "kind": "bool"},
    "IMUNODEPRE":  {"label": "Imunodepressão",         "group": "Comorbidades",   "kind": "bool"},
    "OBESIDADE":   {"label": "Obesidade",              "group": "Comorbidades",   "kind": "bool"},
    "HOSPITALIZ":  {"label": "Hospitalização",         "group": "Contexto",       "kind": "bool"},
    # Demografia / contexto
    "age_years":          {"label": "Idade (anos)",       "group": "Demografia", "kind": "age"},
    "sex_M":              {"label": "Sexo masculino",     "group": "Demografia", "kind": "bool"},
    "uf_code":            {"label": "UF (código IBGE)",   "group": "Demografia", "kind": "uf"},
    "munic_code":         {"label": "Município (código)", "group": "Demografia", "kind": "munic"},
    "notification_month": {"label": "Mês da notificação", "group": "Demografia", "kind": "month"},
    "notification_week":  {"label": "Semana epidemiológica", "group": "Demografia", "kind": "week"},
}


def feature_label(name: str) -> str:
    """Devolve o rótulo humano de uma feature; cai no próprio nome se ausente."""
    return FEATURE_META.get(name, {}).get("label", name)


def feature_group(name: str) -> str:
    return FEATURE_META.get(name, {}).get("group", "Outros")


# ---------------------------------------------------------------------------
# Modelo MLflow (inferência ao vivo) — opcional/defensivo
# ---------------------------------------------------------------------------

def _ensure_pipeline_on_path() -> None:
    """Garante que ``src.models.predict`` é importável a partir do dashboard."""
    candidates = [str(PIPELINE_ROOT), str(PIPELINE_ROOT.parent)]
    for cand in candidates:
        if cand not in sys.path:
            sys.path.insert(0, cand)


@lru_cache(maxsize=1)
def model_available() -> bool:
    """``True`` se os artefatos dos dois modelos existem em disco."""
    disease = MODELS_DIR / "disease_classifier" / "MLmodel"
    severity = MODELS_DIR / "severity_classifier" / "MLmodel"
    return disease.exists() and severity.exists()


@lru_cache(maxsize=1)
def _import_predict_module():
    """Importa ``src.models.predict`` de forma tolerante; ``None`` em falha."""
    _ensure_pipeline_on_path()
    try:
        import importlib

        return importlib.import_module("src.models.predict")
    except Exception:
        return None


def predict_full_safe(features: dict) -> dict | None:
    """Roda os dois classificadores no exemplo informado.

    Devolve ``None`` quando o modelo/MLflow não está disponível — a página
    chamadora deve cair em modo de demonstração.
    """
    mod = _import_predict_module()
    if mod is None or not model_available():
        return None
    try:
        return mod.predict_full(features)
    except Exception:
        return None


def disease_input_example() -> list[dict[str, float]]:
    """Casos exemplo embutidos pelo MLflow no salvamento do modelo."""
    path = MODELS_DIR / "disease_classifier" / "input_example.json"
    raw = _read_json(path)
    if not raw or "columns" not in raw or "data" not in raw:
        return []
    cols = raw["columns"]
    return [dict(zip(cols, row)) for row in raw["data"]]
