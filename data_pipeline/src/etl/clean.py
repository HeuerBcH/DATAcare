"""CLI: limpeza de todos os datasets brutos em `Dados/`.

Uso:
    python -m data_pipeline.src.etl.clean                  # todos
    python -m data_pipeline.src.etl.clean --dataset sinan_dengue
    python -m data_pipeline.src.etl.clean --sample 5000    # dry-run de 5k linhas
"""

from __future__ import annotations

import argparse
import sys
from typing import Iterable

from .cleaners import (
    BaseCleaner,
    PnsCleaner,
    SinanCleaner,
    SragCleaner,
    TaxaIncidCleaner,
)
from .config import DATASETS, DatasetSpec, ensure_dirs
from ..utils.logging_config import get_logger

logger = get_logger("etl.clean")


def _cleaner_for(spec: DatasetSpec) -> BaseCleaner:
    """Mapeia família → classe de cleaner."""
    if spec.family == "sinan":
        return SinanCleaner(spec)
    if spec.family == "srag":
        return SragCleaner(spec)
    if spec.family == "pns":
        return PnsCleaner(spec)
    if spec.family == "taxa_incid":
        return TaxaIncidCleaner(spec)
    raise ValueError(f"Família desconhecida: {spec.family}")


def clean_one(spec: DatasetSpec, *, sample_nrows: int | None = None) -> None:
    cleaner = _cleaner_for(spec)
    out = cleaner.run(sample_nrows=sample_nrows)
    logger.info("OK %s -> %s", spec.name, out)


def clean_many(
    specs: Iterable[DatasetSpec], *, sample_nrows: int | None = None
) -> list[tuple[str, str]]:
    """Limpa cada dataset; coleta falhas e devolve. Não sai do processo.

    O CLI (`main`) decide o exit code; quando chamado pelo orquestrador
    (`run_pipeline`) o caller pode continuar para o split mesmo com
    falhas pontuais.
    """
    failures: list[tuple[str, str]] = []
    for spec in specs:
        try:
            clean_one(spec, sample_nrows=sample_nrows)
        except Exception as exc:  # noqa: BLE001 — relatamos individualmente
            logger.exception("Falha ao limpar %s: %s", spec.name, exc)
            failures.append((spec.name, repr(exc)))
    if failures:
        for name, err in failures:
            logger.error("FALHOU: %s -> %s", name, err)
    return failures


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Limpeza dos datasets brutos do Data Care")
    parser.add_argument(
        "--dataset", "-d",
        action="append",
        choices=sorted(DATASETS.keys()),
        help="Roda apenas estes datasets (pode repetir). Default: todos.",
    )
    parser.add_argument(
        "--sample", "-s",
        type=int,
        default=None,
        help="Lê apenas N linhas (modo dry-run). Default: arquivo inteiro.",
    )
    args = parser.parse_args(argv)

    ensure_dirs()
    selected = [DATASETS[name] for name in (args.dataset or sorted(DATASETS.keys()))]
    logger.info("Datasets a limpar: %s", [s.name for s in selected])
    failures = clean_many(selected, sample_nrows=args.sample)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
