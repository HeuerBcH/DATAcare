"""Unit tests for ML models.

All tests use synthetic data — no real parquet files required.
Run with: pytest data_pipeline/tests/ml/ -v
"""
from __future__ import annotations

import numpy as np
import pytest
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from src.features.build_features import make_synthetic_disease, make_synthetic_severity
from src.features.config import DISEASE_LABELS, SEVERITY_LABELS
from src.models.evaluate import compute_metrics
from src.models.pipeline import build_disease_pipeline, build_severity_pipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def disease_data():
    return make_synthetic_disease(n_per_class=300)


@pytest.fixture(scope="module")
def severity_data():
    return make_synthetic_severity(n_per_class=300)


@pytest.fixture(scope="module")
def trained_disease(disease_data):
    X, y = disease_data
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=0)
    p = build_disease_pipeline()
    p.fit(X_tr, y_tr)
    return p, X_te, y_te, list(X.columns)


@pytest.fixture(scope="module")
def trained_severity(severity_data):
    X, y = severity_data
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=0)
    p = build_severity_pipeline()
    p.fit(X_tr, y_tr)
    return p, X_te, y_te, list(X.columns)


# ---------------------------------------------------------------------------
# Disease pipeline
# ---------------------------------------------------------------------------

class TestDiseasePipeline:
    def test_builds(self):
        assert isinstance(build_disease_pipeline(), Pipeline)

    def test_has_three_steps(self):
        p = build_disease_pipeline()
        assert list(p.named_steps) == ["imputer", "scaler", "clf"]

    def test_fit_predict_shape(self, disease_data):
        X, y = disease_data
        p = build_disease_pipeline()
        p.fit(X, y)
        assert p.predict(X).shape == (len(y),)

    def test_output_classes(self, disease_data):
        X, y = disease_data
        p = build_disease_pipeline()
        p.fit(X, y)
        assert set(p.predict(X)).issubset({0, 1, 2, 3})

    def test_proba_shape(self, trained_disease):
        p, X_te, _, _ = trained_disease
        proba = p.predict_proba(X_te)
        assert proba.shape[1] == 4

    def test_proba_sums_to_one(self, trained_disease):
        p, X_te, _, _ = trained_disease
        proba = p.predict_proba(X_te)
        np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)

    def test_accuracy_above_chance(self, trained_disease):
        p, X_te, y_te, _ = trained_disease
        acc = (p.predict(X_te) == y_te).mean()
        # Random baseline for 4 classes = 0.25; expect significantly better
        assert acc > 0.40, f"Disease classifier accuracy too low: {acc:.3f}"

    def test_handles_missing_features(self, disease_data):
        X, y = disease_data
        p = build_disease_pipeline()
        p.fit(X, y)
        X_with_nan = X.copy()
        X_with_nan.iloc[:5, :5] = np.nan
        preds = p.predict(X_with_nan)
        assert len(preds) == len(y)


# ---------------------------------------------------------------------------
# Severity pipeline
# ---------------------------------------------------------------------------

class TestSeverityPipeline:
    def test_builds(self):
        assert isinstance(build_severity_pipeline(), Pipeline)

    def test_fit_predict_shape(self, severity_data):
        X, y = severity_data
        p = build_severity_pipeline()
        p.fit(X, y)
        assert p.predict(X).shape == (len(y),)

    def test_output_classes(self, severity_data):
        X, y = severity_data
        p = build_severity_pipeline()
        p.fit(X, y)
        assert set(p.predict(X)).issubset({0, 1, 2})

    def test_proba_sums_to_one(self, trained_severity):
        p, X_te, _, _ = trained_severity
        proba = p.predict_proba(X_te)
        np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)

    def test_accuracy_above_chance(self, trained_severity):
        p, X_te, y_te, _ = trained_severity
        acc = (p.predict(X_te) == y_te).mean()
        # Random baseline for 3 classes = 0.33; expect better
        assert acc > 0.45, f"Severity classifier accuracy too low: {acc:.3f}"

    def test_feature_importances_available(self, trained_severity):
        p, _, _, _ = trained_severity
        clf = p.named_steps["clf"]
        assert hasattr(clf, "feature_importances_")
        assert len(clf.feature_importances_) > 0


# ---------------------------------------------------------------------------
# Metrics / report structure
# ---------------------------------------------------------------------------

class TestEvaluateMetrics:
    def test_disease_report_keys(self, trained_disease):
        p, X_te, y_te, feat_names = trained_disease
        report = compute_metrics(p, X_te, y_te, DISEASE_LABELS, "test_disease", feat_names)
        for key in ("accuracy", "macro_f1", "confusion_matrix", "top_features",
                    "f1_per_class", "n_test"):
            assert key in report, f"Missing key: {key}"

    def test_confusion_matrix_shape_disease(self, trained_disease):
        p, X_te, y_te, feat_names = trained_disease
        report = compute_metrics(p, X_te, y_te, DISEASE_LABELS, "test_disease", feat_names)
        cm = report["confusion_matrix"]
        assert len(cm) == 4
        assert all(len(row) == 4 for row in cm)

    def test_severity_report_keys(self, trained_severity):
        p, X_te, y_te, feat_names = trained_severity
        report = compute_metrics(p, X_te, y_te, SEVERITY_LABELS, "test_severity", feat_names)
        for key in ("accuracy", "macro_f1", "confusion_matrix", "top_features"):
            assert key in report

    def test_confusion_matrix_shape_severity(self, trained_severity):
        p, X_te, y_te, feat_names = trained_severity
        report = compute_metrics(p, X_te, y_te, SEVERITY_LABELS, "test_severity", feat_names)
        cm = report["confusion_matrix"]
        assert len(cm) == 3
        assert all(len(row) == 3 for row in cm)

    def test_top_features_max_20(self, trained_disease):
        p, X_te, y_te, feat_names = trained_disease
        report = compute_metrics(p, X_te, y_te, DISEASE_LABELS, "test_disease", feat_names)
        assert len(report["top_features"]) <= 20

    def test_report_json_serializable(self, trained_disease):
        import json
        p, X_te, y_te, feat_names = trained_disease
        report = compute_metrics(p, X_te, y_te, DISEASE_LABELS, "test_disease", feat_names)
        dumped = json.dumps(report, default=str)
        assert len(dumped) > 0


# ---------------------------------------------------------------------------
# Synthetic data generators
# ---------------------------------------------------------------------------

class TestSyntheticGenerators:
    def test_disease_shape(self):
        X, y = make_synthetic_disease(n_per_class=100)
        assert len(X) == 400
        assert len(y) == 400

    def test_disease_all_classes(self):
        _, y = make_synthetic_disease(n_per_class=100)
        assert set(y.unique()) == {0, 1, 2, 3}

    def test_severity_shape(self):
        X, y = make_synthetic_severity(n_per_class=100)
        assert len(X) == 300
        assert len(y) == 300

    def test_severity_all_classes(self):
        _, y = make_synthetic_severity(n_per_class=100)
        assert set(y.unique()) == {0, 1, 2}

    def test_no_all_nan_rows_disease(self):
        X, _ = make_synthetic_disease(n_per_class=100)
        assert X.isna().all(axis=1).sum() == 0

    def test_no_all_nan_rows_severity(self):
        X, _ = make_synthetic_severity(n_per_class=100)
        assert X.isna().all(axis=1).sum() == 0
