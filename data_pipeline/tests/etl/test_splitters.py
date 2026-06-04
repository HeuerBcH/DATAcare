"""Testes anti-contaminação para os splitters.

Os testes são a *defesa principal* contra leakage: cobrem os três
cenários reais — temporal, por grupo, e desbalanceado — e o validador.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Adiciona o root do pipeline ao path para import direto sem instalar pacote.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.etl.config import SplitRatios  # noqa: E402
from src.etl.splitters.strategies import (  # noqa: E402
    GroupedSplitter,
    StratifiedTemporalSplitter,
    TemporalSplitter,
)
from src.etl.splitters.leakage import validate_no_leakage  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temporal_df() -> pd.DataFrame:
    """1000 linhas com datas crescentes — cenário SINAN/SRAG/taxa_incid."""
    dates = pd.date_range("2023-01-01", periods=1000, freq="D")
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "DT_NOTIFIC": dates,
        "CLASSI_FIN": rng.choice(["5", "10", "11"], size=1000),
        "feature_x": rng.normal(size=1000),
    })


@pytest.fixture
def grouped_df() -> pd.DataFrame:
    """200 UPAs com ~10 respondentes cada — cenário PNS."""
    rng = np.random.default_rng(1)
    rows = []
    for upa_id in range(200):
        n = rng.integers(5, 15)
        for _ in range(int(n)):
            rows.append({
                "UPA_PNS": f"UPA_{upa_id:04d}",
                "V0001": rng.choice(["33", "35", "23", "29"]),  # UF
                "A001": rng.choice(["1", "2"]),
                "feature_y": rng.normal(),
            })
    return pd.DataFrame(rows)


@pytest.fixture
def temporal_with_nat() -> pd.DataFrame:
    """200 linhas com 30 datas NaT no meio."""
    dates = pd.date_range("2024-01-01", periods=200, freq="D").to_list()
    dates[50:80] = [pd.NaT] * 30
    rng = np.random.default_rng(2)
    return pd.DataFrame({
        "DT_NOTIFIC": dates,
        "feature_z": rng.normal(size=200),
    })


# ---------------------------------------------------------------------------
# TemporalSplitter — contrato central
# ---------------------------------------------------------------------------

class TestTemporalSplitter:
    def test_split_respects_chronological_order(self, temporal_df):
        splitter = TemporalSplitter("DT_NOTIFIC")
        result = splitter.split(temporal_df)
        assert result.train["DT_NOTIFIC"].max() < result.val["DT_NOTIFIC"].min()
        assert result.val["DT_NOTIFIC"].max() < result.test["DT_NOTIFIC"].min()

    def test_split_proportions_within_tolerance(self, temporal_df):
        splitter = TemporalSplitter("DT_NOTIFIC")
        result = splitter.split(temporal_df)
        total = sum(result.sizes.values())
        assert abs(result.sizes["train"] / total - 0.70) < 0.02
        assert abs(result.sizes["val"] / total - 0.15) < 0.02
        assert abs(result.sizes["test"] / total - 0.15) < 0.02

    def test_no_rows_lost(self, temporal_df):
        splitter = TemporalSplitter("DT_NOTIFIC")
        result = splitter.split(temporal_df)
        assert sum(result.sizes.values()) == len(temporal_df)

    def test_rows_with_nat_go_to_train_not_test(self, temporal_with_nat):
        splitter = TemporalSplitter("DT_NOTIFIC")
        result = splitter.split(temporal_with_nat)
        # Linhas com NaT não podem aparecer em val/test (sem prova de ordem).
        assert result.val["DT_NOTIFIC"].isna().sum() == 0
        assert result.test["DT_NOTIFIC"].isna().sum() == 0
        # Todas as 30 NaT terminam em train.
        assert result.train["DT_NOTIFIC"].isna().sum() == 30

    def test_missing_time_column_raises(self, temporal_df):
        splitter = TemporalSplitter("NAO_EXISTE")
        with pytest.raises(ValueError, match="ausente"):
            splitter.split(temporal_df)

    def test_all_invalid_time_raises(self):
        df = pd.DataFrame({"DT_NOTIFIC": [pd.NaT] * 5, "x": range(5)})
        splitter = TemporalSplitter("DT_NOTIFIC")
        with pytest.raises(ValueError, match="sem valores válidos"):
            splitter.split(df)


# ---------------------------------------------------------------------------
# GroupedSplitter — anti-contaminação por cluster
# ---------------------------------------------------------------------------

class TestGroupedSplitter:
    def test_no_group_appears_in_two_splits(self, grouped_df):
        splitter = GroupedSplitter("UPA_PNS")
        result = splitter.split(grouped_df)
        train_g = set(result.train["UPA_PNS"])
        val_g = set(result.val["UPA_PNS"])
        test_g = set(result.test["UPA_PNS"])
        assert not (train_g & val_g)
        assert not (train_g & test_g)
        assert not (val_g & test_g)

    def test_all_rows_of_a_group_stay_together(self, grouped_df):
        splitter = GroupedSplitter("UPA_PNS")
        result = splitter.split(grouped_df)
        for split_name, df in result.as_dict().items():
            for upa in df["UPA_PNS"].unique():
                expected = (grouped_df["UPA_PNS"] == upa).sum()
                got = (df["UPA_PNS"] == upa).sum()
                assert got == expected, (
                    f"UPA {upa} apareceu particionada em {split_name}: {got}/{expected}"
                )

    def test_no_rows_lost(self, grouped_df):
        splitter = GroupedSplitter("UPA_PNS")
        result = splitter.split(grouped_df)
        assert sum(result.sizes.values()) == len(grouped_df)

    def test_stratified_keeps_class_distribution_roughly(self, grouped_df):
        splitter = GroupedSplitter("UPA_PNS", stratify_column="V0001")
        result = splitter.split(grouped_df)
        # Distribuição de UF não deve divergir grosseiramente entre splits.
        train_dist = result.train["V0001"].value_counts(normalize=True).sort_index()
        test_dist = result.test["V0001"].value_counts(normalize=True).sort_index()
        for uf in train_dist.index.intersection(test_dist.index):
            assert abs(train_dist[uf] - test_dist[uf]) < 0.20

    def test_reproducible_with_same_seed(self, grouped_df):
        a = GroupedSplitter("UPA_PNS", seed=123).split(grouped_df)
        b = GroupedSplitter("UPA_PNS", seed=123).split(grouped_df)
        assert set(a.train["UPA_PNS"]) == set(b.train["UPA_PNS"])
        assert set(a.test["UPA_PNS"]) == set(b.test["UPA_PNS"])

    def test_missing_group_column_raises(self, grouped_df):
        splitter = GroupedSplitter("NAO_EXISTE")
        with pytest.raises(ValueError, match="ausente"):
            splitter.split(grouped_df)


# ---------------------------------------------------------------------------
# StratifiedTemporalSplitter
# ---------------------------------------------------------------------------

class TestStratifiedTemporalSplitter:
    def test_keeps_temporal_order(self, temporal_df):
        splitter = StratifiedTemporalSplitter("DT_NOTIFIC", "CLASSI_FIN")
        result = splitter.split(temporal_df)
        assert result.train["DT_NOTIFIC"].max() < result.val["DT_NOTIFIC"].min()
        assert result.val["DT_NOTIFIC"].max() < result.test["DT_NOTIFIC"].min()


# ---------------------------------------------------------------------------
# Validador de leakage
# ---------------------------------------------------------------------------

class TestLeakageValidator:
    def test_temporal_split_passes_validation(self, temporal_df):
        splitter = TemporalSplitter("DT_NOTIFIC")
        result = splitter.split(temporal_df)
        rep = validate_no_leakage(
            result,
            dataset="test_sinan",
            strategy="temporal",
            time_column="DT_NOTIFIC",
        )
        assert rep.ok, f"Erros inesperados: {rep.errors}"
        assert rep.temporal_order_ok is True
        assert rep.duplicate_rows_across_splits == 0

    def test_grouped_split_passes_validation(self, grouped_df):
        splitter = GroupedSplitter("UPA_PNS")
        result = splitter.split(grouped_df)
        rep = validate_no_leakage(
            result,
            dataset="test_pns",
            strategy="grouped",
            group_column="UPA_PNS",
        )
        assert rep.ok, f"Erros inesperados: {rep.errors}"
        assert all(v == 0 for v in rep.group_overlaps.values())

    def test_validator_detects_injected_group_overlap(self, grouped_df):
        splitter = GroupedSplitter("UPA_PNS")
        result = splitter.split(grouped_df)
        # Injeta linhas do train no test (simulando leakage).
        bad_test = pd.concat([result.test, result.train.head(50)], ignore_index=True)
        bad_result = type(result)(train=result.train, val=result.val, test=bad_test)
        rep = validate_no_leakage(
            bad_result,
            dataset="test_pns_leaky",
            strategy="grouped",
            group_column="UPA_PNS",
        )
        assert not rep.ok
        assert any("UPA_PNS" in e for e in rep.errors)

    def test_validator_detects_temporal_violation(self, temporal_df):
        splitter = TemporalSplitter("DT_NOTIFIC")
        result = splitter.split(temporal_df)
        # Inverte train e test para forçar violação cronológica.
        bad_result = type(result)(train=result.test, val=result.val, test=result.train)
        rep = validate_no_leakage(
            bad_result,
            dataset="test_temporal_leaky",
            strategy="temporal",
            time_column="DT_NOTIFIC",
        )
        assert not rep.ok
        assert rep.temporal_order_ok is False
        assert any("Ordem temporal" in e for e in rep.errors)


# ---------------------------------------------------------------------------
# Ratios
# ---------------------------------------------------------------------------

class TestFallbackSplit:
    """Cobre o caso real `taxa_indic_chikungunya.csv` (co_anomes todo NaN)."""

    def test_fallback_to_grouped_when_time_column_all_nan(self):
        from src.etl.config import DatasetSpec, SplitRatios as _R
        from src.etl.split import _splitter_with_fallback

        spec = DatasetSpec(
            name="x", family="taxa_incid", filename="x.csv",
            time_column="co_anomes",
            split_strategy="temporal",
            fallback_group_column="co_ibge",
        )
        df = pd.DataFrame({
            "co_anomes": [pd.NA] * 100,
            "co_ibge":   [f"M{i % 20:03d}" for i in range(100)],
            "valor":     range(100),
        })
        splitter, strategy, group = _splitter_with_fallback(spec, df, _R())
        assert strategy == "grouped"
        assert group == "co_ibge"

        result = splitter.split(df)
        train_g = set(result.train["co_ibge"])
        val_g = set(result.val["co_ibge"])
        test_g = set(result.test["co_ibge"])
        assert not (train_g & val_g)
        assert not (train_g & test_g)


class TestSplitRatios:
    def test_default_ratios_sum_to_one(self):
        r = SplitRatios()
        assert abs(r.train + r.val + r.test - 1.0) < 1e-6

    def test_sum_above_one_raises(self):
        with pytest.raises(ValueError, match="somar 1.0"):
            SplitRatios(train=0.5, val=0.3, test=0.3)

    def test_sum_below_one_raises(self):
        with pytest.raises(ValueError, match="somar 1.0"):
            SplitRatios(train=0.4, val=0.3, test=0.2)

    def test_negative_ratios_rejected(self):
        """Antes aceitava negativos somando 1.0 (e.g., 1.5/-0.5/0.0)."""
        with pytest.raises(ValueError, match=">= 0"):
            SplitRatios(train=1.5, val=-0.5, test=0.0)

    def test_negative_val_rejected(self):
        with pytest.raises(ValueError, match=">= 0"):
            SplitRatios(train=0.5, val=-0.1, test=0.6)


class TestValidatorWithEmptySplits:
    """Garante que o validador continua detectando leakage quando algum split sai vazio."""

    def test_duplicate_check_still_runs_with_empty_val(self):
        """Train↔test devem ser comparados mesmo quando val está vazio."""
        from src.etl.splitters.strategies import SplitResult
        from src.etl.splitters.leakage import validate_no_leakage

        common = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        result = SplitResult(
            train=common.copy(),
            val=pd.DataFrame(columns=["a", "b"]),
            test=common.copy(),  # exatamente as mesmas linhas → leakage
        )
        rep = validate_no_leakage(
            result, dataset="t", strategy="temporal",
            time_column=None,  # foco no check de duplicatas
            expected_ratios=(0.6, 0.2, 0.2),
            ratio_tolerance=1.0,  # ignora warnings de ratio para isolar o teste
        )
        assert not rep.ok, "deveria detectar 3 linhas duplicadas entre train e test"
        assert rep.duplicate_rows_across_splits == 3

    def test_temporal_check_compares_train_to_test_when_val_empty(self):
        """Com val vazio, train↔test ainda precisa ser checado."""
        from src.etl.splitters.strategies import SplitResult
        from src.etl.splitters.leakage import validate_no_leakage

        # Train tem datas FUTURAS, test tem datas PASSADAS — violação clara.
        train = pd.DataFrame({"t": pd.to_datetime(["2025-01-01", "2025-02-01"])})
        test = pd.DataFrame({"t": pd.to_datetime(["2024-01-01", "2024-02-01"])})
        result = SplitResult(
            train=train, val=pd.DataFrame(columns=["t"]), test=test,
        )
        rep = validate_no_leakage(
            result, dataset="t", strategy="temporal",
            time_column="t",
            expected_ratios=(0.5, 0.0, 0.5),
            ratio_tolerance=1.0,
        )
        assert not rep.ok
        assert rep.temporal_order_ok is False
        assert any("Ordem temporal" in e for e in rep.errors)


class TestGroupedSplitterStratifyFallback:
    """#9: warn quando stratify_column declarado mas ausente do DataFrame."""

    def test_warning_emitted_when_stratify_column_missing(self):
        import logging
        from src.etl.splitters.strategies import logger as splitter_logger

        # O logger do módulo usa `propagate=False` (evita logs duplicados na
        # CLI), então `caplog` do pytest não pega. Anexar um handler local
        # ao logger captura os records diretamente.
        records: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        handler = _Capture(level=logging.WARNING)
        splitter_logger.addHandler(handler)
        try:
            splitter = GroupedSplitter("g", stratify_column="ausente")
            df = pd.DataFrame({"g": [f"G{i%10}" for i in range(100)], "x": range(100)})
            result = splitter.split(df)
        finally:
            splitter_logger.removeHandler(handler)

        assert sum(result.sizes.values()) == 100, "split deve completar mesmo no fallback"
        messages = [r.getMessage() for r in records if r.levelno == logging.WARNING]
        assert any("stratify_column" in m and "ausente do DataFrame" in m for m in messages), (
            f"Esperava warning sobre stratify_column degradada; ficou: {messages}"
        )
