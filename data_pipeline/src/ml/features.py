"""Feature engineering compartilhada do modelo de risco (HU-05).

Fonte ÚNICA da verdade sobre como uma triagem vira features para o modelo de
ML. É usada tanto no treino (data_pipeline) quanto na predição em tempo real da
API Django — garantindo que treino e inferência apliquem exatamente as mesmas
transformações.
"""
from __future__ import annotations

# Catálogos canônicos: (nome, flag). Mantidos aqui para que o treino, o seed do
# banco e os catálogos persistidos fiquem alinhados.
SYMPTOM_CATALOG = [
    ("Febre", False),
    ("Tosse", True),
    ("Falta de ar", True),
    ("Dor de garganta", True),
    ("Coriza", True),
    ("Dor no corpo", False),
    ("Dor de cabeça", False),
    ("Diarreia", False),
    ("Náusea", False),
    ("Fadiga", False),
    ("Tontura", False),
    ("Dor no peito", True),
    ("Perda de apetite", False),
    ("Manchas na pele", False),
]

COMORBIDITY_CATALOG = [
    ("Hipertensão", False),
    ("Diabetes", True),
    ("Asma", True),
    ("DPOC", True),
    ("Doença cardíaca", True),
    ("Obesidade", False),
    ("Insuficiência renal", True),
    ("Câncer", True),
    ("Tabagismo", False),
]

RESPIRATORY_SYMPTOMS = {name for name, resp in SYMPTOM_CATALOG if resp}
CRITICAL_COMORBIDITIES = {name for name, crit in COMORBIDITY_CATALOG if crit}

FEATURE_NAMES = [
    "idade",
    "genero_M",
    "genero_F",
    "num_sintomas",
    "severidade_media",
    "severidade_max",
    "duracao_media",
    "tem_febre",
    "tem_tosse",
    "tem_falta_de_ar",
    "tem_sintoma_respiratorio",
    "num_sintomas_respiratorios",
    "num_comorbidades",
    "tem_diabetes",
    "tem_hipertensao",
    "tem_comorbidade_critica",
    "num_visitas_historico",
]

RISK_LEVELS = ["baixo", "medio", "alto"]


def build_features(record: dict) -> dict:
    """Converte um registro de triagem num dicionário de features.

    Espera::

        record = {
            "age": int,
            "gender": "M" | "F" | "O",
            "symptoms": [{"name": str, "severity": 1-5, "duration_days": int}, ...],
            "comorbidities": [str, ...],
            "num_previous_visits": int,
        }
    """
    symptoms = record.get("symptoms") or []
    comorbidities = record.get("comorbidities") or []
    names = [s.get("name") for s in symptoms]
    severities = [float(s.get("severity") or 0) for s in symptoms]
    durations = [float(s.get("duration_days") or 0) for s in symptoms]

    n_sym = len(symptoms)
    resp = [n for n in names if n in RESPIRATORY_SYMPTOMS]
    gender = (record.get("gender") or "").upper()

    return {
        "idade": float(record.get("age") or 0),
        "genero_M": 1.0 if gender == "M" else 0.0,
        "genero_F": 1.0 if gender == "F" else 0.0,
        "num_sintomas": float(n_sym),
        "severidade_media": (sum(severities) / n_sym) if n_sym else 0.0,
        "severidade_max": max(severities) if severities else 0.0,
        "duracao_media": (sum(durations) / n_sym) if n_sym else 0.0,
        "tem_febre": 1.0 if "Febre" in names else 0.0,
        "tem_tosse": 1.0 if "Tosse" in names else 0.0,
        "tem_falta_de_ar": 1.0 if "Falta de ar" in names else 0.0,
        "tem_sintoma_respiratorio": 1.0 if resp else 0.0,
        "num_sintomas_respiratorios": float(len(resp)),
        "num_comorbidades": float(len(comorbidities)),
        "tem_diabetes": 1.0 if "Diabetes" in comorbidities else 0.0,
        "tem_hipertensao": 1.0 if "Hipertensão" in comorbidities else 0.0,
        "tem_comorbidade_critica": 1.0 if any(c in CRITICAL_COMORBIDITIES for c in comorbidities) else 0.0,
        "num_visitas_historico": float(record.get("num_previous_visits") or 0),
    }


def vectorize(features: dict) -> list:
    """Ordena um dict de features na ordem canônica de FEATURE_NAMES."""
    return [float(features[name]) for name in FEATURE_NAMES]


def rule_based_score(features: dict) -> float:
    """Score de risco 0-100 determinístico, derivado de conhecimento de domínio.

    Usado para (a) rotular os dados sintéticos (com ruído adicionado à parte) e
    (b) servir de fallback na API quando o modelo .joblib ainda não foi treinado.
    """
    f = features
    score = 0.0
    # Idade: risco cresce a partir dos 55 anos.
    score += max(0.0, (f["idade"] - 55.0)) * 0.55
    score += 6.0 if f["idade"] >= 70 else 0.0
    # Severidade e quantidade de sintomas.
    score += f["severidade_media"] * 4.5
    score += f["severidade_max"] * 1.8
    score += f["num_sintomas"] * 1.2
    # Sintomas respiratórios pesam mais (foco SRAG/APS).
    score += f["tem_sintoma_respiratorio"] * 5.0
    score += f["tem_falta_de_ar"] * 11.0
    score += f["tem_febre"] * 3.0
    score += f["num_sintomas_respiratorios"] * 1.5
    # Duração prolongada.
    score += min(f["duracao_media"], 14.0) * 0.5
    # Comorbidades.
    score += f["num_comorbidades"] * 2.8
    score += f["tem_comorbidade_critica"] * 10.0
    score += f["tem_diabetes"] * 3.0
    score += f["tem_hipertensao"] * 2.5
    return float(max(0.0, min(100.0, score)))


def level_from_score(score: float) -> str:
    if score >= 70.0:
        return "alto"
    if score >= 38.0:
        return "medio"
    return "baixo"


def rule_based_risk(record_or_features: dict, *, is_features: bool = False):
    """Retorna (level, score) com base na regra de domínio."""
    features = record_or_features if is_features else build_features(record_or_features)
    score = rule_based_score(features)
    return level_from_score(score), score
