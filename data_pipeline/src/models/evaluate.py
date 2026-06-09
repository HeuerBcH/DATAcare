"""Compute and structure evaluation metrics for trained pipelines."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


def compute_metrics(
    pipeline: Pipeline,
    X_test,
    y_test,
    label_map: dict[int, str],
    model_name: str,
    feature_names: list[str],
) -> dict[str, Any]:
    """
    Run inference on X_test and return a fully structured metrics dict
    that is JSON-serializable and ready to be saved as a model card.
    """
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test) if hasattr(pipeline, "predict_proba") else None

    n_classes = len(label_map)
    target_names = [label_map[i] for i in range(n_classes)]

    acc = float(accuracy_score(y_test, y_pred))
    f1_macro = float(f1_score(y_test, y_pred, average="macro"))
    f1_per_class = f1_score(y_test, y_pred, average=None, labels=list(range(n_classes)))
    cm = confusion_matrix(y_test, y_pred, labels=list(range(n_classes))).tolist()

    clf_report = classification_report(
        y_test, y_pred,
        labels=list(range(n_classes)),
        target_names=target_names,
        output_dict=True,
    )

    # Feature importances from XGBoost clf step
    clf = pipeline.named_steps.get("clf")
    top_features: dict[str, float] = {}
    if clf is not None and hasattr(clf, "feature_importances_"):
        raw = clf.feature_importances_
        pairs = sorted(zip(feature_names, raw.tolist()), key=lambda x: x[1], reverse=True)
        top_features = {k: round(v, 6) for k, v in pairs[:20]}

    return {
        "model_name": model_name,
        "accuracy": round(acc, 4),
        "macro_f1": round(f1_macro, 4),
        "f1_per_class": {
            label_map[i]: round(float(f1_per_class[i]), 4)
            for i in range(n_classes)
        },
        "confusion_matrix": cm,
        "confusion_matrix_labels": target_names,
        "classification_report": clf_report,
        "top_features": top_features,
        "n_test": int(len(y_test)),
        "label_map": label_map,
    }
