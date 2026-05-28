"""Funções de visualização para EDA.

Cada função recebe um DataFrame e um diretório de saída, salva o gráfico em PNG
e retorna o caminho do arquivo. Não exibe nada interativamente (sem plt.show()).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # backend sem GUI — funciona em servidor/CI
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import seaborn as sns

logger = logging.getLogger(__name__)

sns.set_theme(style="whitegrid", palette="muted")
FIGSIZE_WIDE = (14, 5)
FIGSIZE_SQ = (10, 8)
DPI = 120


def plot_missing_heatmap(df: pd.DataFrame, out_dir: Path, slug: str) -> Path:
    """Heatmap de valores ausentes (colunas com >0% de missing)."""
    missing_cols = [c for c in df.columns if df[c].isnull().any()]
    if not missing_cols:
        logger.info("%s: sem valores ausentes — heatmap ignorado", slug)
        return out_dir / "no_missing.txt"

    sample = df[missing_cols].head(5_000).isnull()
    fig, ax = plt.subplots(figsize=(min(len(missing_cols) * 0.4 + 2, 20), 6))
    sns.heatmap(sample.T, cbar=False, ax=ax, xticklabels=False, yticklabels=True, cmap="Reds")
    ax.set_title(f"{slug} — Mapa de valores ausentes (primeiras 5 000 linhas)")
    ax.set_xlabel("Registros")
    plt.tight_layout()
    path = out_dir / "missing_heatmap.png"
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def plot_temporal_series(df: pd.DataFrame, date_col: str, out_dir: Path, slug: str) -> Optional[Path]:
    """Série temporal de notificações por mês."""
    if date_col not in df.columns:
        return None

    dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
    if dates.empty:
        return None

    monthly = dates.dt.to_period("M").value_counts().sort_index()
    monthly.index = monthly.index.to_timestamp()

    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    ax.fill_between(monthly.index, monthly.values, alpha=0.3)
    ax.plot(monthly.index, monthly.values, linewidth=1.5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b/%Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45, ha="right")
    ax.set_title(f"{slug} — Notificações por mês")
    ax.set_ylabel("Quantidade")
    ax.set_xlabel("")
    plt.tight_layout()
    path = out_dir / "temporal_series.png"
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def plot_target_distribution(df: pd.DataFrame, target_col: str, out_dir: Path, slug: str) -> Optional[Path]:
    """Gráfico de barras da variável alvo (CLASSI_FIN)."""
    if target_col not in df.columns:
        return None

    vc = df[target_col].value_counts(dropna=False).head(15)
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(vc.index.astype(str), vc.values)
    ax.bar_label(bars, padding=3, fmt="%d")
    ax.set_title(f"{slug} — Distribuição de {target_col}")
    ax.set_xlabel("Quantidade")
    plt.tight_layout()
    path = out_dir / "target_distribution.png"
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def plot_numeric_distributions(df: pd.DataFrame, out_dir: Path, slug: str, max_cols: int = 12) -> list[Path]:
    """Histogramas das colunas numéricas (até max_cols)."""
    num_cols = df.select_dtypes(include="number").columns.tolist()[:max_cols]
    if not num_cols:
        return []

    ncols = min(3, len(num_cols))
    nrows = -(-len(num_cols) // ncols)  # ceil division
    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 5, nrows * 3.5))
    axes = [axes] if nrows * ncols == 1 else list(axes.flatten())

    for ax, col in zip(axes, num_cols):
        data = df[col].dropna()
        ax.hist(data, bins=30, edgecolor="white", alpha=0.8)
        ax.set_title(col, fontsize=9)
        ax.tick_params(labelsize=8)

    for ax in axes[len(num_cols):]:
        ax.set_visible(False)

    fig.suptitle(f"{slug} — Distribuições numéricas", y=1.01)
    plt.tight_layout()
    path = out_dir / "numeric_distributions.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return [path]


def plot_top_municipios(df: pd.DataFrame, ibge_col: str, out_dir: Path, slug: str, top_n: int = 20) -> Optional[Path]:
    """Top N municípios por volume de notificações."""
    if ibge_col not in df.columns:
        return None

    vc = df[ibge_col].value_counts().head(top_n)
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x=vc.values, y=vc.index.astype(str), ax=ax, orient="h")
    ax.set_title(f"{slug} — Top {top_n} municípios (código IBGE)")
    ax.set_xlabel("Notificações")
    plt.tight_layout()
    path = out_dir / "top_municipios.png"
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path
