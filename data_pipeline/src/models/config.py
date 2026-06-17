"""Model artifact paths and hyperparameter configuration.

Modelos usados (todos do scikit-learn, dentro da lista permitida pela disciplina):
  - Random Forest  -> modelo principal (salvo para serving)
  - Decision Tree  -> modelo de comparação

XGBoost foi removido do projeto.
"""
from __future__ import annotations

import os
from pathlib import Path

from scipy.stats import randint
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

# Label mappings — fonte única em src.features.config; reexportados aqui
# para manter a API histórica (train/predict importam de src.models.config).
from src.features.config import DISEASE_LABELS, SEVERITY_LABELS

_PIPELINE_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = _PIPELINE_ROOT / "models"
ML_REPORTS_DIR = _PIPELINE_ROOT / "data" / "reports" / "ml"

# Paralelismo da busca de hiperparâmetros (RandomizedSearchCV/GridSearchCV).
# Cada worker do search é um PROCESSO separado que duplica os dados de treino e
# constrói uma floresta inteira — com n_jobs=-1 (1 por core) isso multiplica o
# pico de memória e estoura o limite do Docker (OOM / exit 137). Limitamos a um
# valor baixo por padrão; aumente via ML_N_JOBS no .env se tiver mais RAM.
# A Random Forest final continua usando todos os cores (n_jobs=-1, baseada em
# threads que compartilham memória — barato), então o treino segue rápido.
SEARCH_N_JOBS = max(1, int(os.getenv("ML_N_JOBS", "2")))


def model_path(name: str) -> Path:
    """Diretório do modelo MLflow (formato ``mlflow.sklearn``) para serving.

    Ex.: ``models/disease_classifier/`` contendo ``MLmodel``, ``model.pkl``,
    ``conda.yaml`` etc. Substitui o antigo artefato ``<name>.joblib``.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return MODELS_DIR / name


def report_path(name: str) -> Path:
    ML_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return ML_REPORTS_DIR / f"{name}_report.json"


# ---------------------------------------------------------------------------
# Modelos candidatos (lista permitida pela disciplina)
# ---------------------------------------------------------------------------
# Hiperparâmetros default de cada modelo. A busca (Grid/Random) refina-os.

# class_weight="balanced" reponderar as classes pelo inverso da frequência,
# atacando a dominância de dengue (73%) / "baixo" (97%) que fazia o modelo
# ignorar as classes raras (chikungunya, zika, "medio", "alto"). Combina com a
# remoção do vazamento geográfico para que a predição responda aos sintomas.
RANDOM_FOREST_PARAMS: dict = {
    "n_estimators": 250,
    "max_depth": None,
    "min_samples_leaf": 1,
    "n_jobs": -1,
    "class_weight": "balanced",
    "random_state": 42,
}

DECISION_TREE_PARAMS: dict = {
    "max_depth": 30,
    "min_samples_leaf": 2,
    "class_weight": "balanced",
    "random_state": 42,
}


def candidate_estimators() -> dict:
    """Modelos treinados e comparados em cada tarefa (>= 2 modelos da lista).

    Random Forest é o modelo principal (tende a vencer e é salvo p/ serving);
    Decision Tree entra como baseline interpretável para comparação.
    """
    return {
        "random_forest": RandomForestClassifier(**RANDOM_FOREST_PARAMS),
        "decision_tree": DecisionTreeClassifier(**DECISION_TREE_PARAMS),
    }


# ---------------------------------------------------------------------------
# Espaços de busca de hiperparâmetros (por MODELO, não por tarefa)
# ---------------------------------------------------------------------------
# As chaves usam o prefixo "clf__" porque a busca opera sobre o Pipeline
# (imputer -> scaler -> clf), e só queremos variar o classificador.
#
# - PARAM_DIST: distribuições para RandomizedSearchCV (amostragem aleatória).
# - PARAM_GRID: grade discreta para GridSearchCV (busca exaustiva, pequena).

PARAM_DIST: dict = {
    "random_forest": {
        "clf__n_estimators": randint(150, 300),
        "clf__max_depth": randint(14, 30),
        "clf__min_samples_leaf": randint(1, 4),
        # "sqrt"/"log2" mantêm o RF rápido; max_features=None (todas) é lento
        # e desnecessário (não melhora a acurácia neste problema).
        "clf__max_features": ["sqrt", "log2"],
        # reponderação de classes — combate o desbalanceamento extremo.
        "clf__class_weight": ["balanced", "balanced_subsample", None],
    },
    "decision_tree": {
        "clf__max_depth": randint(10, 45),
        "clf__min_samples_leaf": randint(1, 10),
        "clf__criterion": ["gini", "entropy"],
        "clf__class_weight": ["balanced", None],
    },
}

PARAM_GRID: dict = {
    "random_forest": {
        "clf__n_estimators": [200, 300],
        "clf__max_depth": [20, 30],
        "clf__min_samples_leaf": [1, 2],
        "clf__class_weight": ["balanced", "balanced_subsample"],
    },
    "decision_tree": {
        "clf__max_depth": [20, 30, None],
        "clf__criterion": ["gini", "entropy"],
        "clf__class_weight": ["balanced", None],
    },
}


__all__ = [
    "model_path", "report_path",
    "candidate_estimators",
    "RANDOM_FOREST_PARAMS", "DECISION_TREE_PARAMS",
    "DISEASE_LABELS", "SEVERITY_LABELS",
    "PARAM_DIST", "PARAM_GRID",
    "SEARCH_N_JOBS",
]
