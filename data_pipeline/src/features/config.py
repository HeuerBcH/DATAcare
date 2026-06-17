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

# ---------------------------------------------------------------------------
# Geographic features per task — controle de vazamento por proveniência
# ---------------------------------------------------------------------------
# ``munic_code`` (ID_MUNICIP) é um vazamento de alvo (*target leakage*): como
# cada doença é notificada em conjuntos de municípios parcialmente distintos e
# a dengue domina o volume, o código do município vira um proxy quase perfeito
# do arquivo de origem = do rótulo. A árvore aprende "município X ⇒ dengue" em
# vez de aprender sintomas (importância de munic_code chegava a 0.90 no modelo
# de doença). Além disso, no SRAG/influenza o município/UF vêm como TEXTO
# ("SAO PAULO"/"SP"), então viram NaN→0 e funcionam como outro identificador
# trivial da classe.
#
# Por isso, NENHUM código geográfico entra no modelo de doença: a triagem deve
# responder aos sintomas, não à localização. A geografia continua disponível
# como metadado fora de X (dashboards/relatórios), apenas não como feature.
#
# Para reintroduzir um sinal regional legítimo (ex.: surtos são regionais),
# inclua apenas ``"uf_code"`` (27 níveis) — nunca ``"munic_code"`` (milhares de
# níveis ⇒ memorização). Mantemos as listas vazias por padrão (debias máximo).
DISEASE_GEO_COLS: list[str] = []
SEVERITY_GEO_COLS: list[str] = []

# ---------------------------------------------------------------------------
# Features demográficas/temporais por tarefa — controle de vazamento por dataset
# ---------------------------------------------------------------------------
# No modelo de DOENÇA, a idade (``age_years``) e as colunas temporais funcionam
# como *proxy do dataset de origem* (pacientes de SRAG/influenza têm distribuição
# etária e janela de coleta diferentes das arboviroses do SINAN). Com a idade no
# modelo, casos clínicos esparsos eram empurrados para "influenza" mesmo com
# sintomas claros de arbovirose. Removendo-a, a predição passa a responder aos
# sintomas (chikungunya clássico → chikungunya, etc.). A idade pouco discrimina
# *qual* arbovirose — ela é relevante para a SEVERIDADE, onde é mantida.
# age_years (idade real, decodificada) é uma feature clínica legítima: melhora a
# acurácia (~+3 pts) SEM dominar as importâncias (os sintomas continuam no topo)
# e sem reintroduzir o viés. Já o temporal (mês/semana) sobe pouco a acurácia mas
# enfraquece a resposta aos sintomas (proxy de janela de coleta), então fica fora.
DISEASE_DEMO_COLS: list[str] = ["sex_M", "age_years"]
DISEASE_INCLUDE_TEMPORAL: bool = False

# ---------------------------------------------------------------------------
# Severidade por TRIAGEM (Fix 6a) — rótulo alinhado às features previsíveis
# ---------------------------------------------------------------------------
# A definição antiga de "alto" usava óbito/EVOLUCAO — desfecho que NÃO entra
# como feature, tornando o rótulo quase não-aprendível (recall de "alto" ≈ 0).
# Aqui "alto" passa a ser um nível de RISCO clínico de triagem, derivado de
# sinais disponíveis no momento do atendimento (e enviados pelo dashboard):
# idade, nº de comorbidades, sinais de alarme e hospitalização. Assim o rótulo
# fica coerente com as features e o modelo consegue, de fato, prever "alto".
SEVERITY_ALARM_COLS: list[str] = ["PETEQUIA_N", "LEUCOPENIA", "LACO"]
SEVERITY_ELDERLY_AGE: int = 60

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
