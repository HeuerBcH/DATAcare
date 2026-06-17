"""Build scikit-learn Pipelines for disease and severity classifiers.

Todos os classificadores compartilham o mesmo pré-processamento:
    imputer (constante 0) -> StandardScaler -> classificador

O StandardScaler é inócuo para modelos baseados em árvore (RF/DT) e necessário
para modelos sensíveis à escala, mantendo a interface uniforme.
"""
from __future__ import annotations

from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sklearn.ensemble import RandomForestClassifier

from .config import RANDOM_FOREST_PARAMS


def build_pipeline(estimator) -> Pipeline:
    """Pipeline padrão (imputer -> scaler -> clf) para um estimador qualquer."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
        ("scaler", StandardScaler()),
        ("clf", clone(estimator)),
    ])


def build_disease_pipeline() -> Pipeline:
    """Pipeline default do classificador de doença (Random Forest)."""
    return build_pipeline(RandomForestClassifier(**RANDOM_FOREST_PARAMS))


def build_severity_pipeline() -> Pipeline:
    """Pipeline default do classificador de severidade (Random Forest)."""
    return build_pipeline(RandomForestClassifier(**RANDOM_FOREST_PARAMS))
