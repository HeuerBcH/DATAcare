"""CLI de treino do modelo de risco (HU-06) + export para a EDA (HU-04).

Uso (a partir de ``data_pipeline/``, com o venv ativo)::

    python -m src.ml.train
    python -m src.ml.train --n 8000
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .model import MODEL_PATH, save, train
from .synthetic import generate_dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ml.train")

# data_pipeline/
PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
INTERIM_DIR = PIPELINE_ROOT / "data" / "interim"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Treina o modelo de risco DATAcare")
    parser.add_argument("--n", type=int, default=6000, help="nº de triagens sintéticas")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    logger.info("Gerando %s triagens sintéticas...", args.n)
    df = generate_dataset(n=args.n, seed=args.seed)
    logger.info("Distribuição de risco: %s", {k: int(v) for k, v in df["risco"].value_counts().items()})

    # Exporta o dataset para a EDA (HU-04) consumir.
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = INTERIM_DIR / "triagens_sinteticas.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    try:
        df.to_parquet(INTERIM_DIR / "triagens_sinteticas.parquet", index=False)
    except Exception as exc:  # pyarrow ausente não deve travar o treino
        logger.warning("Parquet não gerado (%s)", exc)
    logger.info("Dataset salvo em %s", csv_path)

    logger.info("Treinando modelo...")
    model, metrics = train(df)
    save(model, metrics)
    logger.info("Modelo salvo em %s", MODEL_PATH)
    logger.info("Acurácia=%.3f  F1-macro=%.3f", metrics["accuracy"], metrics["macro_f1"])
    logger.info("Top features: %s", list(metrics["feature_importances"].items())[:5])
    print(json.dumps({"accuracy": metrics["accuracy"], "macro_f1": metrics["macro_f1"]}, indent=2))


if __name__ == "__main__":
    main()
