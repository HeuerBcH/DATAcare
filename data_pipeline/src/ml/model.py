"""Treino, persistência e inferência do modelo de risco (HU-06)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib

from .features import FEATURE_NAMES, RISK_LEVELS, build_features, rule_based_risk

MODEL_VERSION = "risk-rf-v1"

# data_pipeline/models/  (src/ml/ -> src/ -> data_pipeline/)
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
MODEL_PATH = MODELS_DIR / "risk_model.joblib"
METRICS_PATH = MODELS_DIR / "metrics.json"
MODEL_CARD_PATH = MODELS_DIR / "model_card.md"


def build_estimator():
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=250,
                    max_depth=12,
                    min_samples_leaf=5,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def train(df):
    """Treina o modelo a partir de um DataFrame com FEATURE_NAMES + 'risco'."""
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.model_selection import train_test_split

    X = df[FEATURE_NAMES].values
    y = df["risco"].values
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    model = build_estimator()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=RISK_LEVELS).tolist()
    clf = model.named_steps["clf"]
    importances = dict(
        sorted(
            zip(FEATURE_NAMES, (float(v) for v in clf.feature_importances_)),
            key=lambda kv: kv[1],
            reverse=True,
        )
    )
    metrics = {
        "model_version": MODEL_VERSION,
        "n_samples": int(len(df)),
        "accuracy": float(report["accuracy"]),
        "macro_f1": float(report["macro avg"]["f1-score"]),
        "per_class": {lvl: report.get(lvl, {}) for lvl in RISK_LEVELS},
        "confusion_matrix": {"labels": RISK_LEVELS, "matrix": cm},
        "feature_importances": importances,
        "class_distribution": {k: int(v) for k, v in df["risco"].value_counts().items()},
    }
    return model, metrics


def save(model, metrics):
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": model, "feature_names": FEATURE_NAMES, "version": MODEL_VERSION},
        MODEL_PATH,
    )
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    MODEL_CARD_PATH.write_text(_model_card(metrics), encoding="utf-8")


_CACHE = {}


def load_model():
    """Carrega o bundle do modelo (cacheado em processo). None se não existir."""
    if "bundle" in _CACHE:
        return _CACHE["bundle"]
    if not MODEL_PATH.exists():
        return None
    bundle = joblib.load(MODEL_PATH)
    _CACHE["bundle"] = bundle
    return bundle


def predict_risk(record: dict):
    """Prediz ``(risk_level, risk_score 0-100, version)`` para uma triagem.

    Usa o modelo treinado; se ausente, cai para a regra de domínio (robustez na
    demo — a API nunca quebra por falta do .joblib).
    """
    features = build_features(record)
    bundle = load_model()
    if bundle is None:
        level, score = rule_based_risk(features, is_features=True)
        return level, round(score, 1), "rule-based-fallback"

    model = bundle["model"]
    names = bundle.get("feature_names", FEATURE_NAMES)
    x = [[float(features[n]) for n in names]]
    proba = model.predict_proba(x)[0]
    proba_map = {cls: float(p) for cls, p in zip(model.classes_, proba)}
    level = max(proba_map, key=proba_map.get)
    # Índice de risco contínuo 0-100 (médio conta meio peso, alto conta cheio).
    score = 100.0 * (proba_map.get("medio", 0.0) * 0.5 + proba_map.get("alto", 0.0) * 1.0)
    return level, round(score, 1), bundle.get("version", MODEL_VERSION)


def _model_card(metrics) -> str:
    lines = [
        "# Model Card — Modelo de Risco DATAcare",
        "",
        f"- **Versão:** {metrics['model_version']}",
        "- **Algoritmo:** RandomForest (scikit-learn) + StandardScaler",
        f"- **Amostras:** {metrics['n_samples']} (dados sintéticos coerentes)",
        f"- **Acurácia (teste):** {metrics['accuracy']:.3f}",
        f"- **F1 macro:** {metrics['macro_f1']:.3f}",
        f"- **Gerado em:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Objetivo",
        "Classificar o risco de um paciente (BAIXO/MÉDIO/ALTO) a partir da triagem do",
        "ACS, para apoiar a priorização de atendimento. NÃO substitui decisão clínica.",
        "",
        "## Dados de treino",
        "Dados **sintéticos** gerados por regra clínica + ruído (`src/ml/synthetic.py`).",
        "Substituível por dados reais de ACS sem mudar a interface de features.",
        "",
        "## Features",
        ", ".join(f"`{f}`" for f in FEATURE_NAMES),
        "",
        "## Limitações",
        "- Rótulos derivados de regra sintética: o modelo aprende essa regra + ruído.",
        "- Não usar para decisão clínica real sem re-treino com dados reais rotulados.",
        "- Apoio à decisão, nunca substituição do julgamento do profissional.",
    ]
    return "\n".join(lines) + "\n"
