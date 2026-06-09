"""Configuração central do pipeline de ETL.

Centraliza caminhos, metadados de cada fonte de dados e parâmetros de
limpeza/split para evitar magic strings espalhadas pelo código.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Caminhos base
# ---------------------------------------------------------------------------

# Caminhos:
#   PIPELINE_ROOT  = .../DATAcare/data_pipeline
#   DATACARE_ROOT  = .../DATAcare
#   WORKSPACE_ROOT = .../p6           (DATAcare e Dados são irmãos aqui)
PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATACARE_ROOT = PIPELINE_ROOT.parent
WORKSPACE_ROOT = DATACARE_ROOT.parent

# Os dados brutos vivem fora do repo (~2GB) — configurável via env var.
RAW_DATA_DIR = Path(
    os.environ.get("DATACARE_RAW_DIR", str(WORKSPACE_ROOT / "Dados"))
)

DATA_DIR = PIPELINE_ROOT / "data"
INTERIM_DIR = DATA_DIR / "interim"      # após limpeza, antes do split
PROCESSED_DIR = DATA_DIR / "processed"   # train/val/test
REPORTS_DIR = DATA_DIR / "reports"       # relatórios de limpeza e leakage

DEFAULT_ENCODING = "latin-1"
DEFAULT_CHUNKSIZE = 100_000  # linhas por chunk para CSVs grandes

# Seed única usada em todos os splits para reprodutibilidade.
RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Metadados por dataset
# ---------------------------------------------------------------------------

SplitStrategy = Literal["temporal", "grouped", "stratified_temporal"]


@dataclass(frozen=True)
class DatasetSpec:
    """Descreve uma fonte de dados bruta e como deve ser tratada.

    Attributes:
        name: identificador curto e único do dataset.
        family: família lógica (sinan, srag, pns, taxa_incid).
        filename: nome do arquivo dentro de RAW_DATA_DIR.
        separator: separador de coluna do CSV.
        encoding: encoding do arquivo.
        date_columns: colunas com datas para parsing.
        time_column: coluna usada para split temporal.
        group_column: coluna usada para split por grupo (anti-leakage de cluster).
        stratify_column: coluna usada para estratificação de classes.
        split_strategy: estratégia padrão de split.
        quoting: 0=QUOTE_MINIMAL, 1=QUOTE_ALL etc. (csv.QUOTE_*).
    """

    name: str
    family: str
    filename: str
    separator: str = ","
    encoding: str = DEFAULT_ENCODING
    date_columns: tuple[str, ...] = ()
    time_column: str | None = None
    group_column: str | None = None
    stratify_column: str | None = None
    split_strategy: SplitStrategy = "temporal"
    # Fallback usado quando a estratégia padrão é "temporal" mas a coluna
    # de tempo veio sem valores válidos (ex.: taxa_incid_chikungunya, em
    # que `co_anomes` chega como string "nan" da fonte). Tipicamente uma
    # chave geográfica (município) para prevenir leakage espacial.
    fallback_group_column: str | None = None
    quoting: int = 0
    # Colunas categóricas de tipo "sim/não/ignorado" no padrão SINAN
    # (1=sim, 2=não, 9=ignorado). Recodificadas em limpeza.
    yes_no_columns: tuple[str, ...] = ()
    # Colunas numéricas com sentinelas (99, 999, 9999) tratadas como NaN.
    numeric_sentinel_columns: tuple[str, ...] = ()
    sentinels: tuple[int, ...] = (99, 999, 9999)


# Colunas comuns aos SINAN clássicos (dengue, chikungunya, zika).
# Lista pragmática: foi montada da inspeção dos cabeçalhos reais.
_SINAN_YES_NO = (
    "FEBRE", "MIALGIA", "CEFALEIA", "EXANTEMA", "VOMITO", "NAUSEA",
    "DOR_COSTAS", "CONJUNTVIT", "ARTRITE", "ARTRALGIA", "PETEQUIA_N",
    "LEUCOPENIA", "LACO", "DOR_RETRO", "DIABETES", "HEMATOLOG",
    "HEPATOPAT", "RENAL", "HIPERTENSA", "ACIDO_PEPT", "AUTO_IMUNE",
    "HOSPITALIZ",
)

_SINAN_DATES = (
    "DT_NOTIFIC", "DT_SIN_PRI", "DT_INVEST", "DT_OBITO",
    "DT_ENCERRA", "DT_DIGITA", "DT_INTERNA",
)

_SRAG_YES_NO = (
    "FEBRE", "TOSSE", "GARGANTA", "DISPNEIA", "DESC_RESP", "SATURACAO",
    "DIARREIA", "VOMITO", "DOR_ABD", "FADIGA", "PERD_OLFT", "PERD_PALA",
    "FATOR_RISC", "PUERPERA", "CARDIOPATI", "HEMATOLOGI", "SIND_DOWN",
    "HEPATICA", "ASMA", "DIABETES", "NEUROLOGIC", "PNEUMOPATI",
    "IMUNODEPRE", "RENAL", "OBESIDADE", "HOSPITAL", "UTI", "ANTIVIRAL",
    "VACINA", "MAE_VAC", "M_AMAMENTA",
)

_SRAG_DATES = (
    "DT_NOTIFIC", "DT_SIN_PRI", "DT_NASC", "DT_UT_DOSE", "DT_VAC_MAE",
    "DT_DOSEUNI", "DT_1_DOSE", "DT_2_DOSE", "DT_ANTIVIR", "DT_INTERNA",
    "DT_ENTUTI", "DT_SAIDUTI", "DT_RAIOX", "DT_COLETA", "DT_PCR",
    "DT_EVOLUCA", "DT_ENCERRA", "DT_DIGITA",
)


DATASETS: dict[str, DatasetSpec] = {
    "sinan_chikungunya": DatasetSpec(
        name="sinan_chikungunya",
        family="sinan",
        filename="chikungunya_2025.csv",
        date_columns=_SINAN_DATES,
        time_column="DT_NOTIFIC",
        stratify_column="CLASSI_FIN",
        split_strategy="temporal",
        yes_no_columns=_SINAN_YES_NO,
    ),
    "sinan_dengue": DatasetSpec(
        name="sinan_dengue",
        family="sinan",
        filename="dengue_2025.csv",
        date_columns=_SINAN_DATES,
        time_column="DT_NOTIFIC",
        stratify_column="CLASSI_FIN",
        split_strategy="temporal",
        yes_no_columns=_SINAN_YES_NO,
    ),
    "sinan_zika": DatasetSpec(
        name="sinan_zika",
        family="sinan",
        filename="zika_2025.csv",
        date_columns=_SINAN_DATES,
        time_column="DT_NOTIFIC",
        stratify_column="CLASSI_FIN",
        split_strategy="temporal",
        yes_no_columns=_SINAN_YES_NO,
    ),
    "srag_influenza": DatasetSpec(
        name="srag_influenza",
        family="srag",
        filename="influeza_srag_2025.csv",
        separator=";",
        date_columns=_SRAG_DATES,
        time_column="DT_NOTIFIC",
        stratify_column="CLASSI_FIN",
        split_strategy="temporal",
        yes_no_columns=_SRAG_YES_NO,
        quoting=0,
    ),
    "pns_2019": DatasetSpec(
        name="pns_2019",
        family="pns",
        filename="pns2019.csv",
        # PNS é survey clusterizado: agrupar por UPA é obrigatório.
        group_column="UPA_PNS",
        stratify_column="V0001",  # UF
        split_strategy="grouped",
    ),
    "taxa_incid_dengue": DatasetSpec(
        name="taxa_incid_dengue",
        family="taxa_incid",
        filename="taxa_incid_dengue.csv",
        time_column="co_anomes",
        split_strategy="temporal",
        fallback_group_column="co_ibge",
    ),
    "taxa_incid_zika": DatasetSpec(
        name="taxa_incid_zika",
        family="taxa_incid",
        filename="taxa_incid_zika.csv",
        time_column="co_anomes",
        split_strategy="temporal",
        fallback_group_column="co_ibge",
    ),
    "taxa_incid_chikungunya": DatasetSpec(
        name="taxa_incid_chikungunya",
        family="taxa_incid",
        filename="taxa_indic_chikungunya.csv",
        time_column="co_anomes",
        split_strategy="temporal",
        fallback_group_column="co_ibge",
    ),
}


# ---------------------------------------------------------------------------
# Parâmetros de split
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SplitRatios:
    """Proporções treino/validação/teste. Devem somar 1.0."""

    train: float = 0.70
    val: float = 0.15
    test: float = 0.15

    def __post_init__(self) -> None:
        if min(self.train, self.val, self.test) < 0:
            raise ValueError(
                f"Proporções de split devem ser >= 0; recebido "
                f"train={self.train}, val={self.val}, test={self.test}"
            )
        total = self.train + self.val + self.test
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Proporções de split devem somar 1.0; recebido {total:.4f}"
            )


DEFAULT_RATIOS = SplitRatios()


# ---------------------------------------------------------------------------
# Helpers de path
# ---------------------------------------------------------------------------

def interim_path(dataset_name: str) -> Path:
    """Onde o dataset limpo (parquet) é gravado, antes do split."""
    return INTERIM_DIR / f"{dataset_name}.parquet"


def processed_path(dataset_name: str, split: str) -> Path:
    """Onde o dataset particionado é gravado (split = train/val/test)."""
    return PROCESSED_DIR / split / f"{dataset_name}.parquet"


def report_path(dataset_name: str, kind: str) -> Path:
    """Caminho de relatório (cleaning ou leakage) em JSON."""
    return REPORTS_DIR / kind / f"{dataset_name}.json"


def ensure_dirs() -> None:
    """Cria diretórios de saída se ainda não existirem."""
    for d in (INTERIM_DIR, PROCESSED_DIR, REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        (PROCESSED_DIR / split).mkdir(parents=True, exist_ok=True)
    for kind in ("cleaning", "leakage"):
        (REPORTS_DIR / kind).mkdir(parents=True, exist_ok=True)
