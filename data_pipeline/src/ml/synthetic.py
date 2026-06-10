"""Gerador de dados sintéticos coerentes para treinar o modelo de risco.

Os dados reais (~2 GB de SINAN/SRAG/PNS) não estão disponíveis localmente e são
populacionais — não mapeiam diretamente para 'risco do paciente individual'.
Para o MVP, geramos triagens sintéticas realistas cujo rótulo segue uma regra
clínica transparente (``features.rule_based_score``) + ruído, de modo que o
modelo aprenda um sinal não-trivial. Trocar por dados reais de ACS no futuro é
direto (mesma interface de features).
"""
from __future__ import annotations

import random

import numpy as np
import pandas as pd

from .features import (
    COMORBIDITY_CATALOG,
    FEATURE_NAMES,
    SYMPTOM_CATALOG,
    build_features,
    level_from_score,
    rule_based_score,
)

SYMPTOM_NAMES = [name for name, _ in SYMPTOM_CATALOG]
COMORBIDITY_NAMES = [name for name, _ in COMORBIDITY_CATALOG]


def random_record(rng: random.Random) -> dict:
    """Gera um registro de triagem plausível (pré-features)."""
    age = int(min(99, max(0, rng.gauss(45, 22))))
    gender = rng.choice(["M", "F", "F", "M", "O"])
    n_sym = rng.choices([0, 1, 2, 3, 4, 5, 6], weights=[5, 15, 25, 22, 18, 10, 5])[0]
    chosen = rng.sample(SYMPTOM_NAMES, k=min(n_sym, len(SYMPTOM_NAMES)))
    symptoms = [
        {
            "name": name,
            "severity": rng.randint(1, 5),
            "duration_days": rng.choices(
                [1, 2, 3, 5, 7, 10, 14], weights=[20, 20, 18, 15, 12, 8, 7]
            )[0],
        }
        for name in chosen
    ]
    # Comorbidades ficam mais prováveis com a idade.
    base_p = 0.15 + min(0.5, max(0.0, (age - 40) / 120))
    comorbidities = [
        name for name in COMORBIDITY_NAMES if rng.random() < base_p * rng.uniform(0.4, 1.0)
    ]
    num_prev = rng.choices([0, 1, 2, 3, 4, 6, 10], weights=[30, 25, 18, 12, 8, 4, 3])[0]
    return {
        "age": age,
        "gender": gender,
        "symptoms": symptoms,
        "comorbidities": comorbidities,
        "num_previous_visits": num_prev,
    }


def generate_dataset(n: int = 6000, seed: int = 42, noise: float = 8.0) -> pd.DataFrame:
    """Gera um DataFrame com as features + a coluna alvo ``risco``."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        record = random_record(rng)
        feats = build_features(record)
        score = rule_based_score(feats)
        noisy = float(min(100.0, max(0.0, score + np_rng.normal(0, noise))))
        rows.append({**feats, "risco": level_from_score(noisy)})
    return pd.DataFrame(rows, columns=FEATURE_NAMES + ["risco"])
