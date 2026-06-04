"""Utilidades de I/O para CSVs grandes do ETL.

Os arquivos brutos chegam em ~2 GB no total. Carregar tudo em memória
quebra; toda leitura passa por iteradores de chunks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pandas as pd

from .config import DEFAULT_CHUNKSIZE, DatasetSpec


def iter_chunks(
    spec: DatasetSpec,
    path: Path,
    *,
    chunksize: int = DEFAULT_CHUNKSIZE,
    usecols: list[str] | None = None,
    nrows: int | None = None,
) -> Iterator[pd.DataFrame]:
    """Itera chunks de um CSV bruto respeitando o `DatasetSpec`.

    Args:
        spec: metadados do dataset (separador, encoding, datas).
        path: caminho do arquivo no disco.
        chunksize: linhas por chunk.
        usecols: subset de colunas (None = todas).
        nrows: corte para amostragem (None = arquivo inteiro).
    """
    reader = pd.read_csv(
        path,
        sep=spec.separator,
        encoding=spec.encoding,
        chunksize=chunksize,
        usecols=usecols,
        nrows=nrows,
        low_memory=False,
        dtype=str,           # tudo string na entrada; tipos são derivados na limpeza
        keep_default_na=True,
        na_values=["", " ", "NA", "NaN", "null"],
        on_bad_lines="warn",
        quoting=spec.quoting,
    )
    yield from reader


def read_sample(spec: DatasetSpec, path: Path, n: int = 5_000) -> pd.DataFrame:
    """Lê uma amostra inicial do CSV (sem chunking) para inspeção."""
    return pd.read_csv(
        path,
        sep=spec.separator,
        encoding=spec.encoding,
        nrows=n,
        low_memory=False,
        dtype=str,
    )


def read_parquet(path: Path) -> pd.DataFrame:
    """Wrapper conciso para leitura de parquet limpo."""
    return pd.read_parquet(path)
