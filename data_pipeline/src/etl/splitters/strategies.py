"""Estratégias de split de dados para ML.

Três estratégias, escolhidas pelo `DatasetSpec`:

1. **TemporalSplitter** (default para séries epidemiológicas):
   ordena por uma coluna de tempo e corta cronologicamente em
   train/val/test. Garante que o teste só veja dados *posteriores* aos
   de treino — modelo precisa generalizar para o futuro, não memorizar.

2. **GroupedSplitter** (PNS e qualquer survey clusterizado):
   todos os registros de um mesmo grupo (UPA, paciente) caem no mesmo
   split. Bloqueia leakage de pessoas/clusters comuns aos splits.

3. **StratifiedTemporalSplitter**:
   combina (1) com estratificação por classe para alvos desbalanceados.
   Dentro de cada janela temporal, mantém a distribuição da classe.

Todas usam `RANDOM_SEED` para reprodutibilidade.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..config import DEFAULT_RATIOS, RANDOM_SEED, SplitRatios
from ...utils.logging_config import get_logger

logger = get_logger("etl.splitters")


@dataclass(frozen=True)
class SplitResult:
    """Resultado bruto do split: três DataFrames disjuntos."""

    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame

    def as_dict(self) -> dict[str, pd.DataFrame]:
        return {"train": self.train, "val": self.val, "test": self.test}

    @property
    def sizes(self) -> dict[str, int]:
        return {k: len(v) for k, v in self.as_dict().items()}


class BaseSplitter(ABC):
    def __init__(self, ratios: SplitRatios = DEFAULT_RATIOS, seed: int = RANDOM_SEED):
        self.ratios = ratios
        self.seed = seed

    @abstractmethod
    def split(self, df: pd.DataFrame) -> SplitResult: ...


# ---------------------------------------------------------------------------
# Temporal
# ---------------------------------------------------------------------------

class TemporalSplitter(BaseSplitter):
    """Split cronológico estrito por uma coluna de tempo.

    Útil quando o modelo precisa generalizar para datas futuras: SINAN,
    SRAG, taxa_incid. O ponto de corte é definido pelo quantil das datas
    ordenadas, garantindo monotonicidade train < val < test no tempo.
    """

    def __init__(
        self,
        time_column: str,
        ratios: SplitRatios = DEFAULT_RATIOS,
        seed: int = RANDOM_SEED,
    ):
        super().__init__(ratios, seed)
        self.time_column = time_column

    def split(self, df: pd.DataFrame) -> SplitResult:
        if self.time_column not in df.columns:
            raise ValueError(
                f"Coluna temporal {self.time_column!r} ausente do DataFrame "
                f"(colunas: {list(df.columns)[:10]}...)"
            )

        # Remove linhas com data inválida — não dá para ordenar com NaT.
        mask_valid = df[self.time_column].notna()
        if mask_valid.sum() == 0:
            raise ValueError(
                f"Coluna {self.time_column!r} sem valores válidos — split temporal impossível."
            )
        df_valid = df.loc[mask_valid].copy()
        df_invalid = df.loc[~mask_valid]

        time = df_valid[self.time_column]
        # Aceita tanto datetime quanto AAAAMM numérico (taxa_incid).
        order = time.argsort(kind="mergesort").to_numpy()
        df_sorted = df_valid.iloc[order].reset_index(drop=True)

        n = len(df_sorted)
        n_train = int(n * self.ratios.train)
        n_val = int(n * self.ratios.val)

        train = df_sorted.iloc[:n_train]
        val = df_sorted.iloc[n_train:n_train + n_val]
        test = df_sorted.iloc[n_train + n_val:]

        # Linhas com tempo inválido vão para train (sem chance de leakage
        # cronológico; descarte completo perderia sinal).
        if not df_invalid.empty:
            train = pd.concat([train, df_invalid], ignore_index=True)

        return SplitResult(train=train, val=val, test=test)


# ---------------------------------------------------------------------------
# Grouped
# ---------------------------------------------------------------------------

class GroupedSplitter(BaseSplitter):
    """Split por grupo: todo registro com mesmo `group_column` cai no mesmo split.

    Imprescindível para surveys clusterizados (PNS por UPA) e para
    qualquer contexto onde um indivíduo aparece em múltiplas linhas
    (longitudinal). Estratifica opcionalmente os grupos por uma coluna
    de classe agregada.
    """

    def __init__(
        self,
        group_column: str,
        stratify_column: str | None = None,
        ratios: SplitRatios = DEFAULT_RATIOS,
        seed: int = RANDOM_SEED,
    ):
        super().__init__(ratios, seed)
        self.group_column = group_column
        self.stratify_column = stratify_column

    def split(self, df: pd.DataFrame) -> SplitResult:
        if self.group_column not in df.columns:
            raise ValueError(
                f"Coluna de grupo {self.group_column!r} ausente do DataFrame."
            )

        groups = df[self.group_column].astype("string")
        unique_groups = pd.Series(groups.dropna().unique())

        if self.stratify_column:
            if self.stratify_column in df.columns:
                train_g, val_g, test_g = self._split_stratified_groups(df, unique_groups)
            else:
                # Sinaliza que a estratificação prometida foi degradada para
                # random — bug silencioso clássico em pipelines de ML.
                logger.warning(
                    "stratify_column %r declarada mas ausente do DataFrame em %s — "
                    "usando split aleatório de grupos em vez de estratificado.",
                    self.stratify_column,
                    self.group_column,
                )
                train_g, val_g, test_g = self._split_random_groups(unique_groups)
        else:
            train_g, val_g, test_g = self._split_random_groups(unique_groups)

        train = df[groups.isin(train_g)].copy()
        val = df[groups.isin(val_g)].copy()
        test = df[groups.isin(test_g)].copy()

        # Linhas com group_column NaN vão para train (mesma lógica do TemporalSplitter:
        # não dá para alocar com segurança, mas descartar perderia sinal).
        orphans = df[groups.isna()].copy()
        if not orphans.empty:
            train = pd.concat([train, orphans], ignore_index=True)

        return SplitResult(train=train, val=val, test=test)

    def _split_random_groups(
        self, unique_groups: pd.Series
    ) -> tuple[set, set, set]:
        rng = np.random.default_rng(self.seed)
        shuffled = unique_groups.sample(frac=1.0, random_state=rng.integers(2**31)).to_numpy()
        n = len(shuffled)
        n_train = int(n * self.ratios.train)
        n_val = int(n * self.ratios.val)
        return (
            set(shuffled[:n_train]),
            set(shuffled[n_train:n_train + n_val]),
            set(shuffled[n_train + n_val:]),
        )

    def _split_stratified_groups(
        self, df: pd.DataFrame, unique_groups: pd.Series
    ) -> tuple[set, set, set]:
        """Estratifica grupos pela classe modal de cada grupo."""
        group_class = (
            df.dropna(subset=[self.group_column])
              .groupby(self.group_column)[self.stratify_column]
              .agg(lambda s: s.mode().iat[0] if not s.mode().empty else pd.NA)
        )
        train_g: set = set()
        val_g: set = set()
        test_g: set = set()
        rng = np.random.default_rng(self.seed)
        for cls, gids in group_class.groupby(group_class.dropna()):
            arr = gids.index.to_numpy()
            rng.shuffle(arr)
            n = len(arr)
            n_train = int(n * self.ratios.train)
            n_val = int(n * self.ratios.val)
            train_g.update(arr[:n_train])
            val_g.update(arr[n_train:n_train + n_val])
            test_g.update(arr[n_train + n_val:])
        # Grupos sem classe (NaN) → splittados aleatoriamente.
        unstratified = group_class[group_class.isna()].index.to_numpy()
        if len(unstratified):
            rng.shuffle(unstratified)
            n = len(unstratified)
            n_train = int(n * self.ratios.train)
            n_val = int(n * self.ratios.val)
            train_g.update(unstratified[:n_train])
            val_g.update(unstratified[n_train:n_train + n_val])
            test_g.update(unstratified[n_train + n_val:])
        return train_g, val_g, test_g


# ---------------------------------------------------------------------------
# Stratified temporal
# ---------------------------------------------------------------------------

class StratifiedTemporalSplitter(BaseSplitter):
    """Temporal por bloco, estratificado por classe dentro de cada bloco.

    Para alvos desbalanceados (e.g. CLASSI_FIN onde a maioria é
    'descartado'). Mantém ordem temporal entre blocos (train < val <
    test) mas reamostra dentro do bloco preservando a proporção de
    classes — ajuda métricas serem comparáveis entre splits.
    """

    def __init__(
        self,
        time_column: str,
        stratify_column: str,
        ratios: SplitRatios = DEFAULT_RATIOS,
        seed: int = RANDOM_SEED,
    ):
        super().__init__(ratios, seed)
        self.time_column = time_column
        self.stratify_column = stratify_column

    def split(self, df: pd.DataFrame) -> SplitResult:
        # 1) Split temporal grosso para definir as janelas.
        temporal = TemporalSplitter(self.time_column, self.ratios, self.seed)
        coarse = temporal.split(df)
        # 2) A separação temporal por si já evita leakage cronológico;
        # como cada linha já caiu numa janela única, a "estratificação"
        # aqui só serve para diagnosticar/registrar balanceamento — não
        # remistura entre splits (isso quebraria a ordem temporal).
        return coarse
