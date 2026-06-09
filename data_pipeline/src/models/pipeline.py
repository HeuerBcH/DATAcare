"""Build scikit-learn Pipelines for disease and severity classifiers."""
from __future__ import annotations

from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from .config import DISEASE_CLF_PARAMS, SEVERITY_CLF_PARAMS


def build_disease_pipeline() -> Pipeline:
    """
    XGBoost pipeline for arbovirosis classification.
    Imputes missing symptoms as 0 (not reported) before scaling.
    """
    return Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
        ("scaler", StandardScaler()),
        ("clf", XGBClassifier(**DISEASE_CLF_PARAMS)),
    ])


def build_severity_pipeline() -> Pipeline:
    """
    XGBoost pipeline for severity stratification (baixo/medio/alto).
    Same preprocessing as disease pipeline; separate hyperparams.
    """
    return Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
        ("scaler", StandardScaler()),
        ("clf", XGBClassifier(**SEVERITY_CLF_PARAMS)),
    ])
