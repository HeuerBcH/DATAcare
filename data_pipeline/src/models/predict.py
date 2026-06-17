"""Inference module — used by the Django backend to call trained models.

Designed for low-latency calls from API views: models are loaded once
and cached in memory via lru_cache.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import mlflow.sklearn
import pandas as pd
from mlflow.models import Model

from .config import model_path, DISEASE_LABELS, SEVERITY_LABELS

logger = logging.getLogger(__name__)


@lru_cache(maxsize=2)
def _load_artifact(name: str) -> dict:
    """Carrega o modelo MLflow salvo em ``models/<name>/`` e os feature names.

    Os nomes das features vêm do *input schema* (signature) do modelo MLflow —
    é assim que substituímos o antigo dict ``{"pipeline", "feature_names"}`` do
    joblib mantendo a ordem das colunas usada no treino.
    """
    path = model_path(name)
    if not path.exists():
        raise FileNotFoundError(
            f"Trained model not found at {path}. "
            "Run: python -m src.models.train --model all"
        )

    pipeline = mlflow.sklearn.load_model(str(path))

    schema = Model.load(str(path)).get_input_schema()
    feature_names = list(schema.input_names()) if schema is not None else []

    logger.info("Loaded MLflow model: %s (%d features)", name, len(feature_names))
    return {"pipeline": pipeline, "feature_names": feature_names}


def _build_input_frame(features: dict[str, Any], feature_names: list[str]) -> pd.DataFrame:
    """
    Build a single-row DataFrame aligned to the training feature set.
    Missing features default to 0 (not reported).
    """
    row = {col: float(features.get(col, 0.0)) for col in feature_names}
    return pd.DataFrame([row])


def predict_disease(features: dict[str, Any]) -> dict[str, Any]:
    """
    Predict arbovirosis type from symptom/demographic features.

    Args:
        features: dict mapping feature names to numeric values (0/1 for symptoms).
            Unknown keys are ignored; missing keys default to 0.

    Returns:
        {
            "predicted_label": int,
            "predicted_class": str,   # e.g. "dengue"
            "probabilities": { "dengue": 0.72, "chikungunya": 0.15, ... }
        }
    """
    artifact = _load_artifact("disease_classifier")
    pipeline = artifact["pipeline"]
    feature_names: list[str] = artifact["feature_names"]

    X = _build_input_frame(features, feature_names)
    pred_class = int(pipeline.predict(X)[0])
    proba = pipeline.predict_proba(X)[0]

    return {
        "predicted_label": pred_class,
        "predicted_class": DISEASE_LABELS[pred_class],
        "probabilities": {
            DISEASE_LABELS[i]: round(float(p), 4)
            for i, p in enumerate(proba)
        },
    }


def predict_severity(features: dict[str, Any]) -> dict[str, Any]:
    """
    Predict severity level (baixo / medio / alto) from features.

    Args:
        features: dict of symptom/comorbidity/demographic values.

    Returns:
        {
            "predicted_label": int,
            "predicted_class": str,   # e.g. "alto"
            "probabilities": { "baixo": 0.10, "medio": 0.25, "alto": 0.65 }
        }
    """
    artifact = _load_artifact("severity_classifier")
    pipeline = artifact["pipeline"]
    feature_names: list[str] = artifact["feature_names"]

    X = _build_input_frame(features, feature_names)
    pred_class = int(pipeline.predict(X)[0])
    proba = pipeline.predict_proba(X)[0]

    return {
        "predicted_label": pred_class,
        "predicted_class": SEVERITY_LABELS[pred_class],
        "probabilities": {
            SEVERITY_LABELS[i]: round(float(p), 4)
            for i, p in enumerate(proba)
        },
    }


def predict_full(features: dict[str, Any]) -> dict[str, Any]:
    """
    Run both classifiers in sequence.
    The predicted disease is added to features before severity prediction,
    giving the severity model context about the disease type.
    """
    disease_result = predict_disease(features)

    # One-hot encode predicted disease into severity features
    enriched = {**features}
    for label in DISEASE_LABELS.values():
        enriched[f"disease_{label}"] = 1.0 if label == disease_result["predicted_class"] else 0.0

    severity_result = predict_severity(enriched)

    return {
        "disease": disease_result,
        "severity": severity_result,
    }
