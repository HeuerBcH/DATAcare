"""CLI: separa cada dataset limpo em train/val/test e valida anti-leakage.

Uso:
    python -m data_pipeline.src.etl.split                       # todos
    python -m data_pipeline.src.etl.split --dataset sinan_dengue    # um só
    python -m data_pipeline.src.etl.split --train 0.7 --val 0.15 --test 0.15
"""

from __future__ import annotations

import argparse
import sys
from typing import Iterable

import pandas as pd

from .config import (
    DATASETS,
    DEFAULT_RATIOS,
    DatasetSpec,
    SplitRatios,
    ensure_dirs,
    interim_path,
    processed_path,
    report_path,
)
from .splitters import (
    GroupedSplitter,
    StratifiedTemporalSplitter,
    TemporalSplitter,
    validate_no_leakage,
)
from .splitters.strategies import BaseSplitter, SplitResult
from ..utils.logging_config import get_logger

logger = get_logger("etl.split")


def _splitter_for(spec: DatasetSpec, ratios: SplitRatios) -> BaseSplitter:
    """Constrói o splitter conforme a estratégia declarada no DatasetSpec."""
    if spec.split_strategy == "temporal":
        if not spec.time_column:
            raise ValueError(f"{spec.name}: split temporal precisa de time_column.")
        return TemporalSplitter(spec.time_column, ratios=ratios)
    if spec.split_strategy == "grouped":
        if not spec.group_column:
            raise ValueError(f"{spec.name}: split por grupo precisa de group_column.")
        return GroupedSplitter(
            spec.group_column,
            stratify_column=spec.stratify_column,
            ratios=ratios,
        )
    if spec.split_strategy == "stratified_temporal":
        if not (spec.time_column and spec.stratify_column):
            raise ValueError(
                f"{spec.name}: split temporal estratificado precisa de time_column e stratify_column."
            )
        return StratifiedTemporalSplitter(
            spec.time_column, spec.stratify_column, ratios=ratios
        )
    raise ValueError(f"Estratégia desconhecida: {spec.split_strategy}")


def _splitter_with_fallback(
    spec: DatasetSpec, df: pd.DataFrame, ratios: SplitRatios
) -> tuple[BaseSplitter, str, str | None]:
    """Resolve o splitter aplicando fallback quando a estratégia primária não funciona.

    Hoje cobre apenas o caso 'temporal sem time_column válido' (ex.: o
    `taxa_indic_chikungunya.csv` que chega com `co_anomes` todo como
    string `"nan"` na fonte). Se `fallback_group_column` estiver definido,
    cai para um split por grupo nessa coluna, preservando anti-leakage
    geográfico. Retorna (splitter, estratégia_efetiva, group_column_efetivo).
    """
    if spec.split_strategy == "temporal" and spec.time_column:
        if spec.time_column in df.columns and df[spec.time_column].notna().sum() == 0:
            if spec.fallback_group_column and spec.fallback_group_column in df.columns:
                logger.warning(
                    "%s: time_column %r sem valores válidos — caindo para split por grupo em %r.",
                    spec.name, spec.time_column, spec.fallback_group_column,
                )
                return (
                    GroupedSplitter(spec.fallback_group_column, ratios=ratios),
                    "grouped",
                    spec.fallback_group_column,
                )
    return _splitter_for(spec, ratios), spec.split_strategy, spec.group_column


def split_one(spec: DatasetSpec, ratios: SplitRatios) -> bool:
    """Lê parquet limpo, faz o split, grava e valida. Retorna True se OK."""
    src = interim_path(spec.name)
    if not src.exists():
        logger.warning(
            "Parquet limpo ausente para %s (%s) — rode clean.py antes.", spec.name, src
        )
        return False

    df = pd.read_parquet(src)
    logger.info("Lido %s | linhas=%d | colunas=%d", spec.name, len(df), df.shape[1])

    splitter, effective_strategy, effective_group = _splitter_with_fallback(spec, df, ratios)
    result: SplitResult = splitter.split(df)
    logger.info("Split %s | strategy=%s | %s", spec.name, effective_strategy, result.sizes)

    # Grava cada partição.
    for split_name, partition in result.as_dict().items():
        out = processed_path(spec.name, split_name)
        out.parent.mkdir(parents=True, exist_ok=True)
        partition.to_parquet(out, index=False)
        logger.info("  -> %s/%s.parquet (%d linhas)", split_name, spec.name, len(partition))

    # Valida anti-leakage usando a estratégia efetivamente aplicada
    # (pode diferir de spec.split_strategy se houve fallback).
    rep = validate_no_leakage(
        result,
        dataset=spec.name,
        strategy=effective_strategy,
        group_column=effective_group,
        time_column=spec.time_column if effective_strategy != "grouped" else None,
        expected_ratios=(ratios.train, ratios.val, ratios.test),
    )
    rep.write(report_path(spec.name, "leakage"))
    if rep.errors:
        logger.error("LEAKAGE em %s: %s", spec.name, rep.errors)
        return False
    if rep.warnings:
        for w in rep.warnings:
            logger.warning("%s: %s", spec.name, w)
    logger.info("OK %s — sem leakage detectado.", spec.name)
    return True


def split_many(specs: Iterable[DatasetSpec], ratios: SplitRatios) -> list[str]:
    """Particiona cada dataset; devolve nomes dos que falharam. Não sai do processo."""
    failures: list[str] = []
    for spec in specs:
        try:
            ok = split_one(spec, ratios)
            if not ok:
                failures.append(spec.name)
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao split %s", spec.name)
            failures.append(spec.name)
    return failures


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Split treino/val/teste com checagem anti-leakage")
    parser.add_argument(
        "--dataset", "-d",
        action="append",
        choices=sorted(DATASETS.keys()),
        help="Limita a estes datasets. Default: todos.",
    )
    parser.add_argument("--train", type=float, default=DEFAULT_RATIOS.train)
    parser.add_argument("--val", type=float, default=DEFAULT_RATIOS.val)
    parser.add_argument("--test", type=float, default=DEFAULT_RATIOS.test)
    args = parser.parse_args(argv)

    ratios = SplitRatios(train=args.train, val=args.val, test=args.test)
    ensure_dirs()
    selected = [DATASETS[name] for name in (args.dataset or sorted(DATASETS.keys()))]
    logger.info("Datasets a particionar: %s | ratios=%s", [s.name for s in selected], ratios)
    failures = split_many(selected, ratios)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
