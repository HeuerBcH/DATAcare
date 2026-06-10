"""Cleaner base com primitivas compartilhadas (datas, codes, dedup)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator

import numpy as np
import pandas as pd

from ..config import DatasetSpec, RAW_DATA_DIR, interim_path, report_path
from ..io_utils import iter_chunks
from ...utils.logging_config import get_logger


@dataclass
class CleaningReport:
    """Resumo do que aconteceu na limpeza — vira JSON em data/reports/cleaning/."""

    dataset: str
    source_file: str
    started_at: str
    finished_at: str
    raw_rows: int = 0
    cleaned_rows: int = 0
    duplicates_dropped: int = 0
    rows_with_invalid_dates: int = 0
    columns_dropped_all_null: list[str] = field(default_factory=list)
    yes_no_columns_recoded: list[str] = field(default_factory=list)
    date_columns_parsed: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


class BaseCleaner:
    """Cleaner-base. Subclasses sobrescrevem `transform_chunk` para regras específicas."""

    def __init__(self, spec: DatasetSpec):
        self.spec = spec
        self.logger = get_logger(f"etl.cleaner.{spec.name}")
        self.report = CleaningReport(
            dataset=spec.name,
            source_file=spec.filename,
            started_at=_now_iso(),
            finished_at="",
        )

    # ------------------------------------------------------------------
    # Pipeline público
    # ------------------------------------------------------------------

    def run(self, *, sample_nrows: int | None = None) -> Path:
        """Executa a limpeza completa e grava parquet em interim/.

        Estratégia em duas camadas para deduplicação:
        1. **Per-chunk**: `_drop_exact_duplicates` durante `transform_chunk`,
           reduz memória ao consolidar.
        2. **Global**: `drop_duplicates` após concat de todos os chunks,
           pega duplicatas que cruzam fronteiras de chunk (não detectáveis
           per-chunk). Sem essa segunda camada, dois registros idênticos em
           chunks distintos sobreviveriam e disparariam falso erro de
           leakage no split.
        """
        src = RAW_DATA_DIR / self.spec.filename
        if not src.exists():
            raise FileNotFoundError(f"Arquivo bruto não encontrado: {src}")

        self.logger.info(
            "Iniciando limpeza | arquivo=%s | sample=%s", src.name, sample_nrows or "full"
        )

        frames = list(self._iter_clean_chunks(src, sample_nrows=sample_nrows))
        df = (
            pd.concat(frames, ignore_index=True, copy=False)
            if frames
            else pd.DataFrame()
        )

        # Passe global de dedup (camada 2).
        if not df.empty:
            before = len(df)
            df = df.drop_duplicates(ignore_index=True)
            cross_chunk = before - len(df)
            if cross_chunk > 0:
                self.report.duplicates_dropped += cross_chunk
                self.report.notes.append(
                    f"{cross_chunk} duplicatas adicionais removidas no passe global "
                    f"(atravessavam fronteiras de chunk)."
                )

        out_path = interim_path(self.spec.name)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out_path, index=False)
        self.report.cleaned_rows = len(df)
        self.report.finished_at = _now_iso()

        self.report.write(report_path(self.spec.name, "cleaning"))
        self.logger.info(
            "Limpeza concluída | linhas_cruas=%d | linhas_limpas=%d | duplicatas=%d",
            self.report.raw_rows,
            self.report.cleaned_rows,
            self.report.duplicates_dropped,
        )
        return out_path

    # ------------------------------------------------------------------
    # Pipeline interno (lazy / por chunk)
    # ------------------------------------------------------------------

    def _iter_clean_chunks(self, src: Path, *, sample_nrows: int | None) -> Iterator[pd.DataFrame]:
        for chunk in iter_chunks(self.spec, src, nrows=sample_nrows):
            self.report.raw_rows += len(chunk)
            cleaned = self.transform_chunk(chunk)
            if cleaned.empty:
                continue
            yield cleaned

    def transform_chunk(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pipeline padrão de transformação. Subclasses podem estender via super()."""
        df = self._strip_strings(df)
        df = self._parse_dates(df)
        df = self._recode_yes_no(df)
        if self.spec.numeric_sentinel_columns:
            df = self._replace_sentinels(df, list(self.spec.numeric_sentinel_columns))
        df = self._drop_exact_duplicates(df)
        return df

    # ------------------------------------------------------------------
    # Primitivas
    # ------------------------------------------------------------------

    # Strings literais que aparecem em CSVs do SUS no lugar de valores ausentes.
    # Tratadas como NA para que parsing/dedup/split funcionem corretamente.
    _NA_SENTINELS: tuple[str, ...] = ("", "nan", "none", "null", "nat", "na", "-")

    def _strip_strings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Strip + normaliza strings-sentinela (`"nan"`, `"None"`, etc.) para NA."""
        obj_cols = df.select_dtypes(include="object").columns
        sentinels = set(self._NA_SENTINELS)
        for col in obj_cols:
            df[col] = df[col].str.strip()
            is_sentinel = df[col].str.lower().isin(sentinels)
            df[col] = df[col].mask(is_sentinel, pd.NA)
        return df

    def _parse_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Converte colunas declaradas como data; conta linhas com data inválida.

        Tenta primeiro o formato ISO (dayfirst=False, rápido). Para as
        linhas que falharam, tenta `format='mixed', dayfirst=True` a partir
        da **string original** — usa dateutil per-elemento e recupera
        DD/MM/AAAA mesmo quando a coluna mistura ISO + BR.

        Sem `format='mixed'`, pandas 2.0+ rejeita o lote misto e retorna
        NaT para tudo que não é ISO — perda silenciosa de sinal temporal.
        """
        invalid_total = 0
        parsed: list[str] = []
        for col in self.spec.date_columns:
            if col not in df.columns:
                continue
            original = df[col].astype("string")
            before_na = original.isna().sum()
            first = pd.to_datetime(original, errors="coerce", dayfirst=False)
            if first.isna().sum() > before_na:
                fallback = pd.to_datetime(
                    original, errors="coerce", dayfirst=True, format="mixed"
                )
                df[col] = first.fillna(fallback)
            else:
                df[col] = first
            after_na = df[col].isna().sum()
            invalid_total += max(0, after_na - before_na)
            parsed.append(col)
        if parsed:
            for col in parsed:
                if col not in self.report.date_columns_parsed:
                    self.report.date_columns_parsed.append(col)
        self.report.rows_with_invalid_dates += int(invalid_total)
        return df

    def _recode_yes_no(self, df: pd.DataFrame) -> pd.DataFrame:
        """Converte 1=sim, 2=não, 9=ignorado → categórico {1: True, 2: False, 9: NaN}.

        Mantém valores faltantes como NaN; reduz cardinalidade e ambiguidade.
        """
        mapping = {"1": True, "2": False, "9": pd.NA, 1: True, 2: False, 9: pd.NA}
        recoded: list[str] = []
        for col in self.spec.yes_no_columns:
            if col not in df.columns:
                continue
            df[col] = df[col].map(mapping)
            df[col] = df[col].astype("boolean")
            recoded.append(col)
        for col in recoded:
            if col not in self.report.yes_no_columns_recoded:
                self.report.yes_no_columns_recoded.append(col)
        return df

    def _drop_exact_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        before = len(df)
        # `.copy()` evita SettingWithCopyWarning quando há transformações subsequentes.
        df = df.drop_duplicates().copy()
        self.report.duplicates_dropped += before - len(df)
        return df

    def _replace_sentinels(self, df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """Substitui sentinelas numéricas (99, 999, 9999) por NaN nas colunas indicadas."""
        for col in columns:
            if col not in df.columns:
                continue
            numeric = pd.to_numeric(df[col], errors="coerce")
            mask = numeric.isin(self.spec.sentinels)
            df.loc[mask, col] = np.nan
        return df


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
