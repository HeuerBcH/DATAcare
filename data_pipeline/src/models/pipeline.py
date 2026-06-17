"""Build scikit-learn Pipelines for disease and severity classifiers.

Todos os classificadores compartilham o mesmo pré-processamento:
    imputer (constante 0) -> StandardScaler -> classificador

O StandardScaler é inócuo para modelos baseados em árvore (RF/DT) e necessário
para modelos sensíveis à escala, mantendo a interface uniforme.
"""
from __future__ import annotations

from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sklearn.ensemble import RandomForestClassifier

from .config import RANDOM_FOREST_PARAMS

# Folds usados pela calibração de probabilidades. cv=3 triplica o custo de fit
# do modelo final (só do vencedor), mas produz probabilidades suaves/calibradas
# em vez das folhas "puras" (0%/100%) de uma árvore — ver evaluate/predict.
CALIBRATION_CV = 3


def build_pipeline(estimator) -> Pipeline:
    """Pipeline padrão (imputer -> scaler -> clf) para um estimador qualquer."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
        ("scaler", StandardScaler()),
        ("clf", clone(estimator)),
    ])


def build_calibrated(pipeline: Pipeline, cv: int = CALIBRATION_CV) -> CalibratedClassifierCV:
    """Envolve um pipeline em ``CalibratedClassifierCV`` (isotônica).

    A calibração elimina as probabilidades 0%/100% absolutas das árvores
    (Causa C) e produz barras de probabilidade suaves no dashboard. O objeto
    resultante mantém ``predict``/``predict_proba`` e aceita o mesmo DataFrame
    de entrada, então o serving MLflow e o ``predict.py`` continuam idênticos.
    """
    return CalibratedClassifierCV(clone(pipeline), method="isotonic", cv=cv)


def build_disease_pipeline() -> Pipeline:
    """Pipeline default do classificador de doença (Random Forest)."""
    return build_pipeline(RandomForestClassifier(**RANDOM_FOREST_PARAMS))


def build_severity_pipeline() -> Pipeline:
    """Pipeline default do classificador de severidade (Random Forest)."""
    return build_pipeline(RandomForestClassifier(**RANDOM_FOREST_PARAMS))
