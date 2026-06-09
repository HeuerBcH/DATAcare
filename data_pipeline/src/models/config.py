"""Model artifact paths and hyperparameter configuration."""
from __future__ import annotations

from pathlib import Path

_PIPELINE_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = _PIPELINE_ROOT / "models"
ML_REPORTS_DIR = _PIPELINE_ROOT / "data" / "reports" / "ml"


def model_path(name: str) -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return MODELS_DIR / f"{name}.joblib"


def report_path(name: str) -> Path:
    ML_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return ML_REPORTS_DIR / f"{name}_report.json"


# XGBoost — disease classifier (4-class: dengue, chikungunya, zika, influenza)
DISEASE_CLF_PARAMS: dict = {
    "n_estimators": 400,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "multi:softprob",
    "eval_metric": "mlogloss",
    "random_state": 42,
    "n_jobs": -1,
}

# XGBoost — severity classifier (3-class: baixo, medio, alto)
# scale_pos_weight not used directly for multiclass; class_weight handled via sample_weight
SEVERITY_CLF_PARAMS: dict = {
    "n_estimators": 400,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "multi:softprob",
    "eval_metric": "mlogloss",
    "random_state": 42,
    "n_jobs": -1,
}

# Label mappings (imported by evaluate and predict)
DISEASE_LABELS: dict[int, str] = {
    0: "dengue",
    1: "chikungunya",
    2: "zika",
    3: "influenza",
}

SEVERITY_LABELS: dict[int, str] = {
    0: "baixo",
    1: "medio",
    2: "alto",
}
