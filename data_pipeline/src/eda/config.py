"""Configuração do módulo EDA — reutiliza src.etl.config sempre que possível.

Importa diretamente as constantes do pipeline ETL para garantir que caminhos,
slugs e metadados de dataset fiquem em um único lugar (src/etl/config.py).
"""

from __future__ import annotations

from pathlib import Path

from src.etl.config import (
    DATASETS,
    DATA_DIR,
    INTERIM_DIR,
    interim_path,
)

# ─── Diretórios de saída específicos da EDA ───────────────────────────────────
REPORTS_DIR = DATA_DIR / "reports"
EDA_REPORTS_DIR = REPORTS_DIR / "eda"

# ─── Slugs disponíveis (derivados do registry central do ETL) ─────────────────
DATASET_SLUGS: list[str] = list(DATASETS.keys())

# ─── Colunas de interesse para análise exploratória ──────────────────────────
DATE_COL = "DT_NOTIFIC"    # data de notificação — SINAN e SRAG
TARGET_COL = "CLASSI_FIN"  # classificação final — variável alvo dos casos
IBGE_COL = "ID_MUNICIP"    # código IBGE do município


def eda_report_path(slug: str) -> Path:
    EDA_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return EDA_REPORTS_DIR / f"{slug}_eda.json"


def eda_plots_dir(slug: str) -> Path:
    d = EDA_REPORTS_DIR / slug / "plots"
    d.mkdir(parents=True, exist_ok=True)
    return d
