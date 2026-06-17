"""Compute and structure evaluation metrics for trained pipelines."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    recall_score,
)

logger = logging.getLogger(__name__)


def _extract_importances(estimator, feature_names: list[str]) -> dict[str, float]:
    """Top-20 importâncias de features a partir do passo ``clf`` do pipeline.

    Aceita um ``Pipeline`` (imputer -> scaler -> clf). Modelos calibrados
    (``CalibratedClassifierCV``) não expõem ``named_steps``; por isso a função
    de treino passa o pipeline base (não-calibrado) como ``importance_estimator``.
    """
    named_steps = getattr(estimator, "named_steps", None)
    clf = named_steps.get("clf") if named_steps else estimator
    if clf is None or not hasattr(clf, "feature_importances_"):
        return {}
    raw = clf.feature_importances_
    pairs = sorted(zip(feature_names, raw.tolist()), key=lambda x: x[1], reverse=True)
    return {k: round(v, 6) for k, v in pairs[:20]}


def compute_metrics(
    pipeline,
    X_test,
    y_test,
    label_map: dict[int, str],
    model_name: str,
    feature_names: list[str],
    importance_estimator=None,
) -> dict[str, Any]:
    """
    Run inference on X_test and return a fully structured metrics dict
    that is JSON-serializable and ready to be saved as a model card.

    ``importance_estimator`` (opcional): pipeline base não-calibrado de onde
    extrair as importâncias de features quando ``pipeline`` é um modelo
    calibrado que não expõe ``feature_importances_``.
    """
    y_pred = pipeline.predict(X_test)

    n_classes = len(label_map)
    target_names = [label_map[i] for i in range(n_classes)]
    labels = list(range(n_classes))

    acc = float(accuracy_score(y_test, y_pred))
    bal_acc = float(balanced_accuracy_score(y_test, y_pred))
    f1_macro = float(f1_score(y_test, y_pred, average="macro"))
    f1_per_class = f1_score(y_test, y_pred, average=None, labels=labels)
    recall_per_class = recall_score(y_test, y_pred, average=None, labels=labels)
    cm = confusion_matrix(y_test, y_pred, labels=labels).tolist()

    clf_report = classification_report(
        y_test, y_pred,
        labels=labels,
        target_names=target_names,
        output_dict=True,
        zero_division=0,
    )

    top_features = _extract_importances(importance_estimator or pipeline, feature_names)

    return {
        "model_name": model_name,
        "accuracy": round(acc, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "macro_f1": round(f1_macro, 4),
        "f1_per_class": {
            label_map[i]: round(float(f1_per_class[i]), 4)
            for i in range(n_classes)
        },
        "recall_per_class": {
            label_map[i]: round(float(recall_per_class[i]), 4)
            for i in range(n_classes)
        },
        "confusion_matrix": cm,
        "confusion_matrix_labels": target_names,
        "classification_report": clf_report,
        "top_features": top_features,
        "n_test": int(len(y_test)),
        "label_map": label_map,
    }
