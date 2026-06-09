"""Training entry point for DATAcare ML models.

Usage:
    python -m src.models.train --model disease
    python -m src.models.train --model severity
    python -m src.models.train --model all
    python -m src.models.train --model all --synthetic   # CI / no real data
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import joblib
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.utils.class_weight import compute_sample_weight

from src.features.build_features import (
    build_disease_features,
    build_severity_features,
    make_synthetic_disease,
    make_synthetic_severity,
)
from .config import (
    DISEASE_LABELS, SEVERITY_LABELS,
    model_path, report_path,
)
from .evaluate import compute_metrics
from .pipeline import build_disease_pipeline, build_severity_pipeline

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Training functions
# ---------------------------------------------------------------------------

def train_disease(synthetic: bool = False) -> None:
    logger.info("=== Training Disease Classifier ===")

    if synthetic:
        logger.info("--synthetic flag: generating synthetic arbovirosis data")
        X, y = make_synthetic_disease()
    else:
        result = build_disease_features()
        if result is None:
            logger.warning("No real parquet data found — falling back to synthetic")
            X, y = make_synthetic_disease()
        else:
            X, y = result

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # Cross-validation on training set
    pipeline = build_disease_pipeline()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_f1 = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="f1_macro", n_jobs=-1)
    logger.info("CV macro-F1: %.4f ± %.4f", cv_f1.mean(), cv_f1.std())

    pipeline.fit(X_train, y_train)

    report = compute_metrics(
        pipeline, X_test, y_test,
        label_map=DISEASE_LABELS,
        model_name="disease_classifier",
        feature_names=list(X.columns),
    )
    report["cv_f1_mean"] = round(float(cv_f1.mean()), 4)
    report["cv_f1_std"] = round(float(cv_f1.std()), 4)

    _save(pipeline, list(X.columns), "disease_classifier", report)


def train_severity(synthetic: bool = False) -> None:
    logger.info("=== Training Severity Classifier ===")

    if synthetic:
        logger.info("--synthetic flag: generating synthetic severity data")
        X, y = make_synthetic_severity()
    else:
        result = build_severity_features()
        if result is None:
            logger.warning("No real parquet data found — falling back to synthetic")
            X, y = make_synthetic_severity()
        else:
            X, y = result

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # Use sample weights to handle class imbalance (alto cases are rare in real data)
    sample_weights = compute_sample_weight("balanced", y_train)

    pipeline = build_severity_pipeline()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_f1 = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="f1_macro", n_jobs=-1)
    logger.info("CV macro-F1: %.4f ± %.4f", cv_f1.mean(), cv_f1.std())

    # Re-fit on full train with sample weights
    pipeline.fit(X_train, y_train, clf__sample_weight=sample_weights)

    report = compute_metrics(
        pipeline, X_test, y_test,
        label_map=SEVERITY_LABELS,
        model_name="severity_classifier",
        feature_names=list(X.columns),
    )
    report["cv_f1_mean"] = round(float(cv_f1.mean()), 4)
    report["cv_f1_std"] = round(float(cv_f1.std()), 4)

    _save(pipeline, list(X.columns), "severity_classifier", report)


def _save(pipeline, feature_names: list[str], name: str, report: dict) -> None:
    artifact_path = model_path(name)
    joblib.dump({"pipeline": pipeline, "feature_names": feature_names}, artifact_path)
    logger.info("Model saved → %s", artifact_path)

    rep_path = report_path(name)
    rep_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info("Report saved → %s", rep_path)
    logger.info(
        "Results — accuracy: %.4f | macro-F1: %.4f | CV-F1: %.4f ± %.4f",
        report["accuracy"], report["macro_f1"],
        report.get("cv_f1_mean", 0), report.get("cv_f1_std", 0),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(asctime)s %(name)s — %(message)s",
        stream=sys.stdout,
    )

    parser = argparse.ArgumentParser(description="Train DATAcare ML models")
    parser.add_argument(
        "--model",
        choices=["disease", "severity", "all"],
        default="all",
        help="Which model to train (default: all)",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use synthetic data instead of real parquet files",
    )
    args = parser.parse_args()

    if args.model in ("disease", "all"):
        train_disease(synthetic=args.synthetic)
    if args.model in ("severity", "all"):
        train_severity(synthetic=args.synthetic)

    logger.info("Training complete.")


if __name__ == "__main__":
    main()
