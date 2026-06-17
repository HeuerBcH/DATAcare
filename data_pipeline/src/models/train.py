"""Training entry point for DATAcare ML models.

Treina e compara >= 2 modelos da lista permitida (Random Forest e Decision
Tree), seleciona o melhor por validação cruzada e o salva para serving via
MLflow. XGBoost foi removido do projeto.

Usage:
    python -m src.models.train --model all
    python -m src.models.train --model all --search grid
    python -m src.models.train --model all --search random --n-iter 20
    python -m src.models.train --model all --synthetic         # CI / sem dados reais
    python -m src.models.train --model all --max-rows 0        # usar todas as linhas
"""
from __future__ import annotations

import argparse
import gc
import json
import logging
import shutil
import sys
from dataclasses import dataclass

import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.models import infer_signature
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)

from src.features.build_features import (
    build_disease_features,
    build_severity_features,
    make_synthetic_disease,
    make_synthetic_severity,
)
from .config import (
    DISEASE_LABELS, SEVERITY_LABELS,
    PARAM_DIST, PARAM_GRID,
    SEARCH_N_JOBS,
    candidate_estimators,
    model_path, report_path,
)
from .evaluate import compute_metrics
from .pipeline import build_pipeline
from .tracking import setup_experiment

logger = logging.getLogger(__name__)

# Constantes de validação — registradas como parâmetros no MLflow.
TEST_SIZE = 0.2
RANDOM_STATE = 42
CV_N_SPLITS = 5
DEFAULT_MAX_ROWS = 400_000  # cap p/ manter o treino rápido sem perder acurácia


@dataclass
class SearchConfig:
    """Configuração da busca de hiperparâmetros.

    method:
        - "random": RandomizedSearchCV (default) — amostra `n_iter` combinações.
        - "grid":   GridSearchCV — busca exaustiva na grade discreta.
        - "none":   sem busca; usa os hiperparâmetros default do config.py.
    sample_size:
        A busca roda sobre uma subamostra estratificada deste tamanho (custo
        computacional); o modelo final é re-treinado com os melhores
        hiperparâmetros sobre TODO o conjunto de treino. 0 => usa tudo.
    """
    method: str = "random"
    n_iter: int = 12
    cv_folds: int = 3
    sample_size: int = 40_000


# ---------------------------------------------------------------------------
# Hyperparameter search
# ---------------------------------------------------------------------------

def _search_best_params(pipeline, model_name: str, X, y, cfg: SearchConfig):
    """Roda Grid/Random Search e devolve (best_params, best_cv_f1, n_candidates).

    Usa StratifiedKFold (lida com classes desbalanceadas) e otimiza macro-F1.
    Retorna dict vazio quando ``method == "none"``.
    """
    if cfg.method == "none":
        return {}, None, 0

    space = PARAM_GRID[model_name] if cfg.method == "grid" else PARAM_DIST[model_name]

    X_s, y_s = X, y
    n = len(y_s)
    if cfg.sample_size and n > cfg.sample_size:
        X_s, _, y_s, _ = train_test_split(
            X, y, train_size=cfg.sample_size, stratify=y, random_state=RANDOM_STATE
        )
        logger.info("Search em subamostra estratificada: %d de %d linhas", len(y_s), n)

    search_cv = StratifiedKFold(n_splits=cfg.cv_folds, shuffle=True, random_state=RANDOM_STATE)
    # n_jobs limitado (SEARCH_N_JOBS) p/ não duplicar os dados em todos os cores
    # e estourar a memória do Docker (OOM). Veja config.SEARCH_N_JOBS.
    if cfg.method == "grid":
        search = GridSearchCV(pipeline, space, scoring="f1_macro",
                              cv=search_cv, n_jobs=SEARCH_N_JOBS)
    else:
        search = RandomizedSearchCV(
            pipeline, space, n_iter=cfg.n_iter, scoring="f1_macro",
            cv=search_cv, n_jobs=SEARCH_N_JOBS, random_state=RANDOM_STATE,
        )

    logger.info("Busca de hiperparametros (%s) em %s...", cfg.method, model_name)
    search.fit(X_s, y_s)
    n_candidates = len(search.cv_results_["params"])
    logger.info(
        "  melhor CV macro-F1 (%d candidatos): %.4f | params: %s",
        n_candidates, search.best_score_, search.best_params_,
    )
    return dict(search.best_params_), float(search.best_score_), n_candidates


def _build_search_params(cfg: SearchConfig, best_cv: float | None, n_candidates: int) -> dict:
    out: dict = {"search_method": cfg.method}
    if cfg.method == "none":
        return out
    out["search_cv_folds"] = cfg.cv_folds
    out["search_sample_size"] = cfg.sample_size
    out["search_n_candidates"] = n_candidates
    if best_cv is not None:
        out["search_best_cv_f1"] = round(best_cv, 4)
    if cfg.method == "random":
        out["search_n_iter"] = cfg.n_iter
    return out


# ---------------------------------------------------------------------------
# Severity resampling
# ---------------------------------------------------------------------------

def _resample_severity(X, y):
    """Balance the severity training set via undersampling + SMOTE."""
    import numpy as np
    from imblearn.over_sampling import SMOTE
    from imblearn.under_sampling import RandomUnderSampler
    from sklearn.impute import SimpleImputer

    y_arr = np.asarray(y)
    unique, cts = np.unique(y_arr, return_counts=True)
    counts = dict(zip(unique.tolist(), cts.tolist()))
    logger.info("Before resampling: %s", counts)

    n_medio = counts.get(1, 0)
    n_alto = counts.get(2, 0)
    if n_medio == 0 or n_alto == 0:
        logger.warning("Skipping resampling — missing minority class")
        return X, y_arr

    imputer = SimpleImputer(strategy="constant", fill_value=0.0)
    X = imputer.fit_transform(X)

    # Undersample 'baixo' (0) a 10x 'médio' (máx 300K), limitado ao disponível.
    n_baixo = counts.get(0, 0)
    target_baixo = min(n_medio * 10, 300_000, n_baixo)
    under = RandomUnderSampler(sampling_strategy={0: target_baixo}, random_state=42)
    X_res, y_res = under.fit_resample(X, y_arr)

    # SMOTE 'alto' (2) até igualar 'médio'.
    k = min(5, n_alto - 1)
    smote = SMOTE(sampling_strategy={2: n_medio}, k_neighbors=k, random_state=42)
    X_res, y_res = smote.fit_resample(X_res, y_res)

    counts_after = {v: int((y_res == v).sum()) for v in (0, 1, 2)}
    logger.info("After resampling:  %s", counts_after)
    return X_res, y_res


# ---------------------------------------------------------------------------
# MLflow logging helpers
# ---------------------------------------------------------------------------

def _model_io(pipeline, X_example):
    """Produz (signature, input_example) de forma robusta.

    Converte a amostra para float (colunas booleanas do pandas quebram o
    ``fillna``/serialização do MLflow) antes de inferir a signature.
    """
    sample = X_example.head(min(50, len(X_example))).copy()
    sample = sample.apply(pd.to_numeric, errors="coerce").astype("float64")
    input_example = sample.head(2).fillna(0.0)
    try:
        signature = infer_signature(sample, pipeline.predict(sample))
    except Exception as exc:
        logger.warning("Não foi possível inferir a signature: %s", exc)
        signature = None
    return signature, input_example


def _log_run(pipeline, params: dict, report: dict, X_example) -> None:
    """Loga parâmetros, métricas, model card e o modelo no run ativo."""
    mlflow.log_params(params)

    mlflow.log_metric("accuracy", report["accuracy"])
    mlflow.log_metric("macro_f1", report["macro_f1"])
    for cls_label, value in report.get("f1_per_class", {}).items():
        mlflow.log_metric(f"f1_{cls_label}", value)
    if "cv_f1_mean" in report:
        mlflow.log_metric("cv_f1_mean", report["cv_f1_mean"])
        mlflow.log_metric("cv_f1_std", report["cv_f1_std"])

    try:
        mlflow.log_dict(report, "reports/model_card.json")
    except Exception as exc:
        logger.warning("Falha ao logar model card: %s", exc)

    signature, input_example = _model_io(pipeline, X_example)
    mlflow.sklearn.log_model(
        sk_model=pipeline, artifact_path="model",
        signature=signature, input_example=input_example,
    )


def _save_serving_model(pipeline, task: str, X_example) -> None:
    """Salva o melhor modelo em models/<task> (formato MLflow) para o backend."""
    signature, input_example = _model_io(pipeline, X_example)
    serving_dir = model_path(task)
    if serving_dir.exists():
        shutil.rmtree(serving_dir)
    mlflow.sklearn.save_model(
        sk_model=pipeline, path=str(serving_dir),
        signature=signature, input_example=input_example,
    )
    logger.info("Serving model saved -> %s", serving_dir)


def _persist_report(name: str, report: dict) -> None:
    rep_path = report_path(name)
    rep_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info("Report saved -> %s", rep_path)


# ---------------------------------------------------------------------------
# Generic task trainer (compara múltiplos modelos)
# ---------------------------------------------------------------------------

def _maybe_subsample(X, y, max_rows: int):
    if max_rows and len(y) > max_rows:
        X_s, _, y_s, _ = train_test_split(
            X, y, train_size=max_rows, stratify=y, random_state=RANDOM_STATE
        )
        logger.info("Subamostragem estratificada do dataset: %d de %d linhas", len(y_s), len(y))
        return X_s, y_s
    return X, y


def _train_task(task, label_map, X, y, data_source, search: SearchConfig,
                resample: bool, max_rows: int):
    logger.info("=== Treinando %s (comparando %d modelos) ===",
                task, len(candidate_estimators()))

    X, y = _maybe_subsample(X, y, max_rows)
    setup_experiment(task)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    if resample:
        X_train, y_train = _resample_severity(X_train, y_train)

    feature_names = list(X.columns)
    cv = StratifiedKFold(n_splits=CV_N_SPLITS, shuffle=True, random_state=RANDOM_STATE)

    leaderboard: list[dict] = []
    best = None  # (cv_f1_mean, model_name, pipeline, report)

    for model_name, estimator in candidate_estimators().items():
        with mlflow.start_run(run_name=f"{task}-{model_name}-{search.method}"):
            pipeline = build_pipeline(estimator)

            best_params, best_cv, n_cand = _search_best_params(
                pipeline, model_name, X_train, y_train, search
            )
            if best_params:
                pipeline.set_params(**best_params)

            cv_f1 = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="f1_macro")
            pipeline.fit(X_train, y_train)

            report = compute_metrics(
                pipeline, X_test, y_test,
                label_map=label_map, model_name=task, feature_names=feature_names,
            )
            report["algorithm"] = model_name
            report["cv_f1_mean"] = round(float(cv_f1.mean()), 4)
            report["cv_f1_std"] = round(float(cv_f1.std()), 4)

            tuned = {k.replace("clf__", ""): v for k, v in best_params.items()}
            params = {
                "algorithm": model_name,
                **tuned,
                **_build_search_params(search, best_cv, n_cand),
                "data_source": data_source,
                "validation": "holdout + StratifiedKFold",
                "test_size": TEST_SIZE,
                "cv_n_splits": CV_N_SPLITS,
                "stratified_split": True,
                "random_state": RANDOM_STATE,
                "n_train": int(len(y_train)),
                "n_test": int(len(X_test)),
                "n_features": len(feature_names),
                "n_classes": len(label_map),
            }
            if resample:
                params["resampling"] = "RandomUnderSampler + SMOTE"

            _log_run(pipeline, params, report, X_test)

            logger.info(
                "[%s] %-14s acc=%.4f | macro-F1=%.4f | CV-F1=%.4f +/- %.4f",
                task, model_name, report["accuracy"], report["macro_f1"],
                report["cv_f1_mean"], report["cv_f1_std"],
            )
            leaderboard.append({
                "algorithm": model_name,
                "accuracy": report["accuracy"],
                "macro_f1": report["macro_f1"],
                "cv_f1_mean": report["cv_f1_mean"],
            })

            score = report["cv_f1_mean"]
            if best is None or score > best[0]:
                best = (score, model_name, pipeline, report)

    # Seleção do melhor modelo (por CV macro-F1) -> serving + relatório canônico.
    _, best_name, best_pipeline, best_report = best
    best_report["leaderboard"] = leaderboard
    best_report["selected_model"] = best_name
    logger.info(
        ">>> Melhor modelo para %s: %s (CV-F1=%.4f | acc=%.4f | macro-F1=%.4f)",
        task, best_name, best[0], best_report["accuracy"], best_report["macro_f1"],
    )
    _persist_report(task, best_report)
    _save_serving_model(best_pipeline, task, X_test)
    return best_report


# ---------------------------------------------------------------------------
# Data loading + public training functions
# ---------------------------------------------------------------------------

def _load_disease(synthetic: bool):
    if synthetic:
        logger.info("--synthetic: gerando dados sintéticos de arbovirose")
        return (*make_synthetic_disease(), "synthetic")
    result = build_disease_features()
    if result is None:
        logger.warning("Sem parquet real — usando dados sintéticos")
        return (*make_synthetic_disease(), "synthetic")
    return (*result, "real_parquet")


def _load_severity(synthetic: bool):
    if synthetic:
        logger.info("--synthetic: gerando dados sintéticos de severidade")
        return (*make_synthetic_severity(), "synthetic")
    result = build_severity_features()
    if result is None:
        logger.warning("Sem parquet real — usando dados sintéticos")
        return (*make_synthetic_severity(), "synthetic")
    return (*result, "real_parquet")


def train_disease(synthetic: bool = False, search: SearchConfig | None = None,
                  max_rows: int = DEFAULT_MAX_ROWS) -> None:
    X, y, data_source = _load_disease(synthetic)
    _train_task("disease_classifier", DISEASE_LABELS, X, y, data_source,
                search or SearchConfig(), resample=False, max_rows=max_rows)


def train_severity(synthetic: bool = False, search: SearchConfig | None = None,
                   max_rows: int = DEFAULT_MAX_ROWS) -> None:
    X, y, data_source = _load_severity(synthetic)
    _train_task("severity_classifier", SEVERITY_LABELS, X, y, data_source,
                search or SearchConfig(), resample=True, max_rows=max_rows)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(asctime)s %(name)s - %(message)s",
        stream=sys.stdout,
    )

    parser = argparse.ArgumentParser(description="Train DATAcare ML models")
    parser.add_argument("--model", choices=["disease", "severity", "all"], default="all")
    parser.add_argument("--synthetic", action="store_true",
                        help="Usar dados sintéticos em vez dos parquets reais")
    parser.add_argument("--search", choices=["none", "random", "grid"], default="random",
                        help="Estratégia de busca de hiperparâmetros (default: random)")
    parser.add_argument("--n-iter", type=int, default=12,
                        help="Nº de combinações do RandomizedSearchCV (default: 12)")
    parser.add_argument("--search-cv", type=int, default=3,
                        help="Folds do StratifiedKFold durante a busca (default: 3)")
    parser.add_argument("--search-sample", type=int, default=40_000,
                        help="Subamostra para a busca; 0 = tudo (default: 40000)")
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS,
                        help=f"Cap de linhas do dataset; 0 = todas (default: {DEFAULT_MAX_ROWS})")
    args = parser.parse_args()

    search = SearchConfig(
        method=args.search, n_iter=args.n_iter,
        cv_folds=args.search_cv, sample_size=args.search_sample,
    )
    logger.info("Search config: %s | max_rows=%s", search, args.max_rows)

    if args.model in ("disease", "all"):
        train_disease(synthetic=args.synthetic, search=search, max_rows=args.max_rows)
        # Libera as matrizes/modelos do disease antes do severity recarregar os
        # parquets — evita que os picos das duas tarefas se somem (OOM).
        gc.collect()
    if args.model in ("severity", "all"):
        train_severity(synthetic=args.synthetic, search=search, max_rows=args.max_rows)

    logger.info("Training complete.")


if __name__ == "__main__":
    main()
