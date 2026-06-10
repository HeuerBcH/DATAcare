"""Testes do módulo de ML (data_pipeline/src/ml), importável via sys.path do settings."""
from src.ml.features import FEATURE_NAMES, build_features, rule_based_risk
from src.ml.model import predict_risk
from src.ml.synthetic import generate_dataset


def test_build_features_has_all_keys():
    rec = {
        "age": 70,
        "gender": "M",
        "symptoms": [{"name": "Febre", "severity": 4, "duration_days": 3}],
        "comorbidities": ["Diabetes"],
        "num_previous_visits": 2,
    }
    f = build_features(rec)
    assert set(f.keys()) == set(FEATURE_NAMES)
    assert f["tem_febre"] == 1.0
    assert f["tem_diabetes"] == 1.0
    assert f["idade"] == 70.0
    assert f["genero_M"] == 1.0 and f["genero_F"] == 0.0


def test_rule_based_score_is_monotonic():
    mild = {"age": 20, "gender": "F", "symptoms": [], "comorbidities": [], "num_previous_visits": 0}
    severe = {
        "age": 82,
        "gender": "M",
        "symptoms": [
            {"name": "Falta de ar", "severity": 5, "duration_days": 5},
            {"name": "Febre", "severity": 5, "duration_days": 4},
        ],
        "comorbidities": ["Diabetes", "Doença cardíaca"],
        "num_previous_visits": 3,
    }
    _, score_mild = rule_based_risk(mild)
    _, score_severe = rule_based_risk(severe)
    assert score_severe > score_mild


def test_synthetic_dataset_shape_and_labels():
    df = generate_dataset(n=200, seed=1)
    assert len(df) == 200
    assert "risco" in df.columns
    assert set(df["risco"].unique()).issubset({"baixo", "medio", "alto"})


def test_predict_risk_returns_valid_output():
    rec = {
        "age": 80,
        "gender": "M",
        "symptoms": [{"name": "Falta de ar", "severity": 5, "duration_days": 3}],
        "comorbidities": ["Diabetes"],
        "num_previous_visits": 1,
    }
    level, score, version = predict_risk(rec)
    assert level in {"baixo", "medio", "alto"}
    assert 0 <= score <= 100
    assert isinstance(version, str)
