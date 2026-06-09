"""
Safe wrapper around the data_pipeline ML models.
Handles ImportError (models not installed) and FileNotFoundError
(models not trained yet) without crashing the API.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PIPELINE_DIR = str(Path(__file__).resolve().parents[3] / "data_pipeline")


def _ensure_path() -> None:
    if _PIPELINE_DIR not in sys.path:
        sys.path.insert(0, _PIPELINE_DIR)


def predict_full(features: dict[str, Any]) -> dict | None:
    """
    Run disease + severity classifiers.

    Returns:
        {
          "disease":  {"predicted_class": "dengue", "probabilities": {...}},
          "severity": {"predicted_class": "alto",   "probabilities": {...}},
        }
    or None if models are unavailable (not trained or deps missing).
    """
    _ensure_path()
    try:
        from src.models.predict import predict_full as _predict  # type: ignore
        return _predict(features)
    except FileNotFoundError:
        logger.warning(
            "ML models not found at %s/models/. "
            "Train them with: PYTHONPATH=data_pipeline python -m src.models.train --model all",
            _PIPELINE_DIR,
        )
        return None
    except ImportError as exc:
        logger.error("ML import failed (missing deps?): %s", exc)
        return None
    except Exception as exc:
        logger.exception("Unexpected prediction error: %s", exc)
        return None
