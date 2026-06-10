"""Testes unitários para src/eda/stats.py.

Usam DataFrames sintéticos — não dependem dos datasets reais (que ficam
fora do repositório no Google Drive).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.eda.stats import (
    basic_info,
    categorical_summary,
    duplicate_analysis,
    geographic_summary,
    missing_values,
    numeric_summary,
    target_distribution,
    temporal_summary,
)


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    np.random.seed(42)
    n = 200
    return pd.DataFrame(
        {
            "DT_NOTIFIC": pd.date_range("2024-01-01", periods=n, freq="D"),
            "CLASSI_FIN": np.random.choice([1, 2, 9, None], size=n),
            "ID_MUNICIP": np.random.choice(["261160", "261400", "330455", None], size=n),
            "IDADE": np.random.randint(0, 90, size=n).astype(float),
            "FEBRE": np.random.choice([1, 2, 9, None], size=n),
            "UF": np.random.choice(["PE", "RJ", "SP"], size=n),
        }
    )


class TestBasicInfo:
    def test_shape(self, sample_df):
        info = basic_info(sample_df)
        assert info["n_rows"] == 200
        assert info["n_cols"] == 6

    def test_memory_positive(self, sample_df):
        assert basic_info(sample_df)["memory_mb"] > 0

    def test_dtypes_keys(self, sample_df):
        info = basic_info(sample_df)
        assert set(info["dtypes"].keys()) == set(sample_df.columns)


class TestMissingValues:
    def test_detects_nulls(self, sample_df):
        result = missing_values(sample_df)
        assert result["total_missing_cells"] > 0

    def test_complete_rows_between_0_and_100(self, sample_df):
        pct = missing_values(sample_df)["pct_complete_rows"]
        assert 0 <= pct <= 100

    def test_no_missing_df(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = missing_values(df)
        assert result["total_missing_cells"] == 0
        assert result["by_column"] == {}


class TestNumericSummary:
    def test_returns_dict_for_numeric_cols(self, sample_df):
        result = numeric_summary(sample_df)
        assert "IDADE" in result

    def test_keys_present(self, sample_df):
        result = numeric_summary(sample_df)
        for col_stats in result.values():
            assert "mean" in col_stats
            assert "std" in col_stats

    def test_empty_if_no_numeric(self):
        df = pd.DataFrame({"a": ["x", "y"], "b": ["p", "q"]})
        assert numeric_summary(df) == {}


class TestCategoricalSummary:
    def test_detects_object_cols(self, sample_df):
        result = categorical_summary(sample_df)
        assert "UF" in result

    def test_n_unique(self, sample_df):
        result = categorical_summary(sample_df)
        assert result["UF"]["n_unique"] == 3


class TestTemporalSummary:
    def test_valid_date_col(self, sample_df):
        result = temporal_summary(sample_df, "DT_NOTIFIC")
        assert "min_date" in result
        assert "monthly_counts" in result
        assert result["pct_valid_dates"] == 100.0

    def test_missing_col(self, sample_df):
        result = temporal_summary(sample_df, "NONEXISTENT")
        assert "error" in result

    def test_with_null_dates(self):
        df = pd.DataFrame({"DT_NOTIFIC": [None, None, "2024-01-01"]})
        result = temporal_summary(df, "DT_NOTIFIC")
        assert result["pct_valid_dates"] < 100


class TestTargetDistribution:
    def test_with_valid_col(self, sample_df):
        result = target_distribution(sample_df, "CLASSI_FIN")
        assert "distribution" in result
        assert result["n_unique"] >= 1

    def test_missing_col(self, sample_df):
        result = target_distribution(sample_df, "NONEXISTENT")
        assert "error" in result


class TestGeographicSummary:
    def test_with_valid_col(self, sample_df):
        result = geographic_summary(sample_df, "ID_MUNICIP")
        assert "n_unique_municipios" in result
        assert "top_municipios" in result

    def test_missing_col(self, sample_df):
        result = geographic_summary(sample_df, "NONEXISTENT")
        assert "error" in result


class TestDuplicateAnalysis:
    def test_no_duplicates(self, sample_df):
        result = duplicate_analysis(sample_df)
        assert result["n_duplicates"] >= 0

    def test_detects_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": [3, 3, 4]})
        result = duplicate_analysis(df)
        assert result["n_duplicates"] == 1
        assert result["pct_duplicates"] > 0
