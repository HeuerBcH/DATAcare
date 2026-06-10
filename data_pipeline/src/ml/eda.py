"""EDA do dataset sintético de triagem (HU-04).

Gera estatísticas e gráficos a partir de ``data/interim/triagens_sinteticas.csv``
(produzido por ``src.ml.train``) — a base que alimenta o modelo de risco.
Saídas em ``data/reports/eda/triagem/``.

    python -m src.ml.eda
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .features import FEATURE_NAMES  # noqa: E402

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
CSV = PIPELINE_ROOT / "data" / "interim" / "triagens_sinteticas.csv"
OUT = PIPELINE_ROOT / "data" / "reports" / "eda" / "triagem"
PLOTS = OUT / "plots"

ORDER = ["baixo", "medio", "alto"]
COLORS = {"baixo": "#16a34a", "medio": "#f59e0b", "alto": "#dc2626"}


def main():
    if not CSV.exists():
        raise SystemExit(f"Dataset não encontrado: {CSV}\nRode antes: python -m src.ml.train")
    PLOTS.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CSV)

    summary = {
        "n_amostras": int(len(df)),
        "distribuicao_risco": {k: int(v) for k, v in df["risco"].value_counts().items()},
        "valores_ausentes": int(df.isna().sum().sum()),
        "describe": json.loads(df[FEATURE_NAMES].describe().to_json()),
        "media_por_risco": json.loads(df.groupby("risco")[FEATURE_NAMES].mean().to_json()),
    }
    (OUT / "eda_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    counts = df["risco"].value_counts().reindex(ORDER).fillna(0)
    plt.figure(figsize=(6, 4))
    plt.bar(ORDER, counts.values, color=[COLORS[o] for o in ORDER])
    plt.title("Distribuição de risco")
    plt.ylabel("nº de triagens")
    plt.tight_layout()
    plt.savefig(PLOTS / "distribuicao_risco.png", dpi=110)
    plt.close()

    plt.figure(figsize=(6, 4))
    plt.boxplot([df[df["risco"] == o]["idade"] for o in ORDER], labels=ORDER)
    plt.title("Idade por nível de risco")
    plt.ylabel("idade")
    plt.tight_layout()
    plt.savefig(PLOTS / "idade_por_risco.png", dpi=110)
    plt.close()

    plt.figure(figsize=(6, 4))
    means = df.groupby("risco")["severidade_media"].mean().reindex(ORDER)
    plt.bar(ORDER, means.values, color=[COLORS[o] for o in ORDER])
    plt.title("Severidade média por nível de risco")
    plt.ylabel("severidade média")
    plt.tight_layout()
    plt.savefig(PLOTS / "severidade_por_risco.png", dpi=110)
    plt.close()

    corr = df[FEATURE_NAMES].corr()
    plt.figure(figsize=(9, 8))
    im = plt.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    plt.colorbar(im, fraction=0.046)
    plt.xticks(range(len(FEATURE_NAMES)), FEATURE_NAMES, rotation=90, fontsize=7)
    plt.yticks(range(len(FEATURE_NAMES)), FEATURE_NAMES, fontsize=7)
    plt.title("Correlação entre features")
    plt.tight_layout()
    plt.savefig(PLOTS / "correlacao_features.png", dpi=110)
    plt.close()

    means_by = df.groupby("risco")[FEATURE_NAMES].mean().reindex(ORDER).round(2)
    md = [
        "# EDA — Triagens sintéticas (HU-04)",
        "",
        f"- Amostras: **{summary['n_amostras']}**",
        f"- Distribuição de risco: **{summary['distribuicao_risco']}**",
        f"- Valores ausentes: **{summary['valores_ausentes']}**",
        "",
        "## Gráficos",
        "![Distribuição de risco](plots/distribuicao_risco.png)",
        "![Idade por risco](plots/idade_por_risco.png)",
        "![Severidade por risco](plots/severidade_por_risco.png)",
        "![Correlação](plots/correlacao_features.png)",
        "",
        "## Média das features por nível de risco",
        "",
        "```",
        means_by.to_string(),
        "```",
    ]
    (OUT / "eda_report.md").write_text("\n".join(md), encoding="utf-8")
    print("EDA salva em", OUT)
    print("Distribuição:", summary["distribuicao_risco"])


if __name__ == "__main__":
    main()
