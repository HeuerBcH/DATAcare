"""Orquestrador da EDA (HU-04).

Executa a análise exploratória completa sobre os parquets limpos produzidos
pelo pipeline ETL (src/etl/run_pipeline.py). Para cada dataset disponível
em data/interim/, gera:
  - Um relatório JSON em data/reports/eda/<slug>_eda.json
  - Gráficos PNG em data/reports/eda/<slug>/plots/

Uso:
    # Todos os datasets disponíveis em data/interim/
    python -m src.eda.run_eda

    # Dataset específico
    python -m src.eda.run_eda --dataset sinan_dengue

    # Listar datasets disponíveis sem processar
    python -m src.eda.run_eda --list
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from .config import (
    DATE_COL,
    DATASET_SLUGS,
    IBGE_COL,
    TARGET_COL,
    eda_plots_dir,
    eda_report_path,
    interim_path,
)
from . import stats as st
from . import plots as pl
from .report import build_report, save_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("eda.run")


def available_datasets() -> list[str]:
    return [slug for slug in DATASET_SLUGS if interim_path(slug).exists()]


def run_dataset(slug: str) -> Path:
    """Executa EDA completa para um dataset e retorna o caminho do relatório."""
    parquet = interim_path(slug)
    if not parquet.exists():
        raise FileNotFoundError(
            f"Parquet não encontrado: {parquet}\n"
            "Execute primeiro: python -m src.etl.run_pipeline"
        )

    logger.info("Carregando %s ...", slug)
    df = pd.read_parquet(parquet)
    logger.info("%s: %d linhas × %d colunas", slug, *df.shape)

    plots_dir = eda_plots_dir(slug)

    # ── estatísticas ─────────────────────────────────────────────────────────
    basic = st.basic_info(df)
    missing = st.missing_values(df)
    numeric = st.numeric_summary(df)
    categorical = st.categorical_summary(df)
    temporal = st.temporal_summary(df, DATE_COL)
    target = st.target_distribution(df, TARGET_COL)
    geographic = st.geographic_summary(df, IBGE_COL)
    duplicates = st.duplicate_analysis(df)

    # ── gráficos ─────────────────────────────────────────────────────────────
    saved_plots: list[Path] = []
    try:
        saved_plots.append(pl.plot_missing_heatmap(df, plots_dir, slug))
        ts = pl.plot_temporal_series(df, DATE_COL, plots_dir, slug)
        if ts:
            saved_plots.append(ts)
        td = pl.plot_target_distribution(df, TARGET_COL, plots_dir, slug)
        if td:
            saved_plots.append(td)
        saved_plots.extend(pl.plot_numeric_distributions(df, plots_dir, slug))
        mun = pl.plot_top_municipios(df, IBGE_COL, plots_dir, slug)
        if mun:
            saved_plots.append(mun)
    except Exception as exc:
        logger.warning("Erro ao gerar gráficos para %s: %s", slug, exc)

    # ── relatório ─────────────────────────────────────────────────────────────
    report = build_report(slug, basic, missing, numeric, categorical, temporal, target, geographic, duplicates, saved_plots)
    out = eda_report_path(slug)
    save_report(report, out)

    logger.info(
        "%s — EDA concluída: %d colunas, %.1f%% linhas completas, %d gráficos",
        slug,
        basic["n_cols"],
        missing.get("pct_complete_rows", 0),
        len([p for p in saved_plots if p and Path(p).exists()]),
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="EDA — DATAcare HU-04")
    parser.add_argument("--dataset", help="Slug do dataset (ex: sinan_dengue). Omitir = todos disponíveis.")
    parser.add_argument("--list", action="store_true", help="Lista datasets disponíveis e sai.")
    args = parser.parse_args()

    if args.list:
        available = available_datasets()
        if available:
            print("Datasets disponíveis em data/interim/:")
            for s in available:
                print(f"  • {s}")
        else:
            print("Nenhum parquet encontrado em data/interim/. Rode o pipeline ETL primeiro.")
        sys.exit(0)

    targets = [args.dataset] if args.dataset else available_datasets()
    if not targets:
        logger.error("Nenhum dataset encontrado em data/interim/. Rode: python -m src.etl.run_pipeline")
        sys.exit(1)

    errors: list[str] = []
    for slug in targets:
        try:
            run_dataset(slug)
        except FileNotFoundError as exc:
            logger.error(exc)
            errors.append(slug)
        except Exception as exc:
            logger.exception("Erro inesperado em %s: %s", slug, exc)
            errors.append(slug)

    if errors:
        logger.warning("Datasets com erro: %s", ", ".join(errors))
        sys.exit(1)

    logger.info("EDA concluída para %d dataset(s).", len(targets) - len(errors))


if __name__ == "__main__":
    main()
