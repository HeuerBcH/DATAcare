"""MLflow tracking configuration for DATAcare ML models.

Centraliza a configuração do MLflow para que `train.py` (e qualquer outro
ponto futuro) compartilhem o mesmo tracking URI e a mesma convenção de
nomes de experimentos.

Decisões de design
------------------
- **Tracking URI local por padrão** (`data_pipeline/mlruns`): file store, não
  exige servidor rodando, e é versionável/reprodutível em Docker. Pode ser
  sobrescrito pela variável de ambiente ``MLFLOW_TRACKING_URI`` (ex.: apontar
  para um servidor ``http://mlflow:5000`` no docker-compose).
- **Múltiplos experimentos**: cada tarefa de classificação tem seu próprio
  experimento (`EXPERIMENTS`), de modo que os runs de doença e severidade
  ficam separados e comparáveis na UI do MLflow.

Para abrir a UI depois de treinar::

    mlflow ui --backend-store-uri data_pipeline/mlruns
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import mlflow

logger = logging.getLogger(__name__)

# Raiz do data_pipeline (…/data_pipeline)
_PIPELINE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_MLRUNS_DIR = _PIPELINE_ROOT / "mlruns"

# Nomes de experimento — um por tarefa de classificação (múltiplos experimentos).
EXPERIMENTS: dict[str, str] = {
    "disease_classifier": "datacare-disease-classification",
    "severity_classifier": "datacare-severity-classification",
}


def get_tracking_uri() -> str:
    """Retorna o tracking URI: env var se definida, senão o file store local."""
    env_uri = os.getenv("MLFLOW_TRACKING_URI")
    if env_uri:
        return env_uri
    _DEFAULT_MLRUNS_DIR.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_MLRUNS_DIR.as_uri()


def setup_experiment(model_name: str) -> str:
    """
    Configura o tracking URI e ativa o experimento da tarefa `model_name`.

    Args:
        model_name: chave em EXPERIMENTS (ex.: "disease_classifier").

    Returns:
        O nome do experimento ativado.
    """
    tracking_uri = get_tracking_uri()
    mlflow.set_tracking_uri(tracking_uri)

    experiment_name = EXPERIMENTS.get(model_name, f"datacare-{model_name}")
    mlflow.set_experiment(experiment_name)

    logger.info("MLflow tracking URI: %s", tracking_uri)
    logger.info("MLflow experiment:   %s", experiment_name)
    return experiment_name
