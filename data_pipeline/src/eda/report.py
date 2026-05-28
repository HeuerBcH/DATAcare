"""Geração do relatório de qualidade de dados em JSON.

Agrega os resultados dos módulos stats e plots em um dicionário
estruturado e o serializa em JSON no diretório de relatórios do EDA.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def build_report(
    slug: str,
    basic: dict,
    missing: dict,
    numeric: dict,
    categorical: dict,
    temporal: dict,
    target: dict,
    geographic: dict,
    duplicates: dict,
    plots: list[Path],
) -> dict[str, Any]:
    return {
        "dataset": slug,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "basic_info": basic,
        "data_quality": {
            "missing_values": missing,
            "duplicates": duplicates,
        },
        "descriptive": {
            "numeric": numeric,
            "categorical": categorical,
        },
        "temporal": temporal,
        "target_variable": target,
        "geographic": geographic,
        "plots": [str(p) for p in plots if p and p.exists()],
    }


def save_report(report: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Relatório EDA salvo em %s", out_path)


def load_report(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
