"""Feature configuration: column groups, label mappings, and derived field definitions."""
from __future__ import annotations

# Symptom columns present in SINAN datasets after ETL cleaning.
# Values after cleaning: 1.0 = sim, 0.0 = nao, NaN = ignorado/ausente
SINAN_SYMPTOM_COLS: list[str] = [
    "FEBRE", "MIALGIA", "CEFALEIA", "EXANTEMA", "VOMITO", "NAUSEA",
    "DOR_COSTAS", "CONJUNTVIT", "ARTRITE", "ARTRALGIA", "PETEQUIA_N",
    "LEUCOPENIA", "LACO", "DOR_RETRO",
]

SINAN_COMORBIDITY_COLS: list[str] = [
    "DIABETES", "HEMATOLOG", "HEPATOPAT", "RENAL",
    "HIPERTENSA", "ACIDO_PEPT", "AUTO_IMUNE",
]

# Symptom columns in SRAG after ETL cleaning
SRAG_SYMPTOM_COLS: list[str] = [
    "FEBRE", "TOSSE", "GARGANTA", "DISPNEIA", "DESC_RESP",
    "DIARREIA", "VOMITO", "FADIGA",
]

SRAG_COMORBIDITY_COLS: list[str] = [
    "CARDIOPATI", "DIABETES", "NEUROLOGIC", "PNEUMOPATI",
    "IMUNODEPRE", "RENAL", "OBESIDADE",
]

# Demographic / temporal columns present across datasets
DEMO_COLS: list[str] = ["NU_IDADE_N", "CS_SEXO"]

# SINAN CLASSI_FIN numeric codes → severity label
# 10 = dengue sem sinais de alarme  → baixo
# 11 = dengue com sinais de alarme  → medio
# 12 = dengue grave                 → alto
# 13 = dengue + óbito               → alto
# 5  = descartado                   → baixo (used when kept in dataset)
SINAN_CLASSI_FIN_TO_SEVERITY: dict[int, int] = {
    5: 0,
    10: 0,
    11: 1,
    12: 2,
    13: 2,
}

# Integer label → human-readable class name
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
