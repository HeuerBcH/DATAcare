"""Orquestrador: clean → split em uma chamada.

Uso:
    python -m data_pipeline.src.etl.run_pipeline
    python -m data_pipeline.src.etl.run_pipeline --sample 10000   # dry-run
    python -m data_pipeline.src.etl.run_pipeline --dataset sinan_zika
"""

from __future__ import annotations

import argparse

from . import clean, split
from .config import DATASETS, DEFAULT_RATIOS, SplitRatios, ensure_dirs
from ..utils.logging_config import get_logger

logger = get_logger("etl.pipeline")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Pipeline completo: limpeza + split")
    parser.add_argument(
        "--dataset", "-d",
        action="append",
        choices=sorted(DATASETS.keys()),
        help="Limita a estes datasets. Default: todos.",
    )
    parser.add_argument("--sample", type=int, default=None, help="N linhas para dry-run.")
    parser.add_argument("--train", type=float, default=DEFAULT_RATIOS.train)
    parser.add_argument("--val", type=float, default=DEFAULT_RATIOS.val)
    parser.add_argument("--test", type=float, default=DEFAULT_RATIOS.test)
    args = parser.parse_args(argv)

    ensure_dirs()
    names = args.dataset or sorted(DATASETS.keys())
    specs = [DATASETS[n] for n in names]

    logger.info("===== Etapa 1/2: limpeza =====")
    clean_failures = clean.clean_many(specs, sample_nrows=args.sample)

    logger.info("===== Etapa 2/2: split =====")
    ratios = SplitRatios(train=args.train, val=args.val, test=args.test)
    # Pula datasets cuja limpeza falhou — split.split_one também tolera
    # parquet ausente, mas filtrar aqui dá log mais limpo.
    failed_names = {name for name, _ in clean_failures}
    survivors = [s for s in specs if s.name not in failed_names]
    if failed_names:
        logger.warning("Pulando split para datasets que falharam na limpeza: %s", sorted(failed_names))
    split_failures = split.split_many(survivors, ratios)

    if clean_failures or split_failures:
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
