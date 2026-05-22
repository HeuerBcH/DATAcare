"""Validação anti-contaminação entre splits.

Roda **depois** de qualquer split e responde 4 perguntas:

1. Há índices duplicados (linha exata) entre splits?
2. Há sobreposição de chaves de grupo (UPA/paciente/município)?
3. A ordem temporal é estritamente train < val < test?
4. As proporções saíram dentro do esperado?

Falha alta = aborta o pipeline. Falha leve (proporção fora por 1–2 p.p.)
= warning.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

from .strategies import SplitResult


@dataclass
class LeakageReport:
    dataset: str
    strategy: str
    sizes: dict[str, int] = field(default_factory=dict)
    ratios: dict[str, float] = field(default_factory=dict)
    group_overlaps: dict[str, int] = field(default_factory=dict)
    temporal_order_ok: bool | None = None
    duplicate_rows_across_splits: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return asdict(self)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def validate_no_leakage(
    result: SplitResult,
    *,
    dataset: str,
    strategy: str,
    group_column: str | None = None,
    time_column: str | None = None,
    expected_ratios: tuple[float, float, float] = (0.70, 0.15, 0.15),
    ratio_tolerance: float = 0.05,
) -> LeakageReport:
    """Executa todos os checks anti-contaminação e devolve relatório."""
    rep = LeakageReport(dataset=dataset, strategy=strategy)
    rep.sizes = result.sizes
    total = sum(rep.sizes.values()) or 1
    rep.ratios = {k: v / total for k, v in rep.sizes.items()}

    _check_no_duplicate_rows(result, rep)
    if group_column:
        _check_no_group_overlap(result, group_column, rep)
    if time_column:
        _check_temporal_order(result, time_column, rep)
    _check_ratios(rep, expected_ratios, ratio_tolerance)
    return rep


def _check_no_duplicate_rows(result: SplitResult, rep: LeakageReport) -> None:
    """Conta linhas idênticas (hash de todas as colunas) compartilhadas entre splits.

    Checa cada par de splits **não-vazios** individualmente; antes desligava
    todo o check quando QUALQUER split estava vazio, mascarando leakage real
    entre os splits que sobrevivem (e.g., train↔test com val vazio).

    `hash_pandas_object` trata NaN/NA consistentemente em qualquer dtype.
    """
    splits = result.as_dict()
    non_empty = {name: df for name, df in splits.items() if not df.empty}
    if len(non_empty) < 2:
        rep.warnings.append(
            "Menos de 2 splits não-vazios — checagem de duplicatas pulada."
        )
        return
    sets = {
        name: set(pd.util.hash_pandas_object(df, index=False).tolist())
        for name, df in non_empty.items()
    }
    names = list(non_empty.keys())
    overlaps = 0
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            overlaps += len(sets[a] & sets[b])
    rep.duplicate_rows_across_splits = overlaps
    if overlaps > 0:
        rep.errors.append(
            f"{overlaps} linhas idênticas (hash) aparecem em mais de um split — leakage."
        )


def _check_no_group_overlap(
    result: SplitResult, group_column: str, rep: LeakageReport
) -> None:
    splits = result.as_dict()
    if group_column not in splits["train"].columns:
        rep.warnings.append(f"Coluna de grupo {group_column!r} ausente — overlap não checado.")
        return
    groups = {
        name: set(df[group_column].dropna().astype("string").unique())
        for name, df in splits.items()
    }
    pairs = [("train", "val"), ("train", "test"), ("val", "test")]
    for a, b in pairs:
        inter = groups[a] & groups[b]
        rep.group_overlaps[f"{a}_x_{b}"] = len(inter)
        if inter:
            rep.errors.append(
                f"{len(inter)} valores de {group_column!r} aparecem em {a} e {b} simultaneamente."
            )


def _check_temporal_order(
    result: SplitResult, time_column: str, rep: LeakageReport
) -> None:
    """Garante ordem cronológica entre splits não-vazios.

    Itera sobre splits **presentes** (não-vazios e com a coluna de tempo
    válida), comparando pares adjacentes. Se `val` estiver vazio, compara
    `train` com `test` diretamente — antes essa checagem era pulada,
    deixando passar leakage temporal entre train e test.
    """
    splits = result.as_dict()
    maxes: dict[str, object] = {}
    mins: dict[str, object] = {}
    for name, df in splits.items():
        if df.empty or time_column not in df.columns:
            continue
        s = df[time_column].dropna()
        if s.empty:
            continue
        mins[name] = s.min()
        maxes[name] = s.max()

    canonical = ["train", "val", "test"]
    present = [n for n in canonical if n in maxes]

    if len(present) < 2:
        rep.warnings.append(
            "Menos de 2 splits com tempo válido — ordem temporal não checada."
        )
        rep.temporal_order_ok = None
        return

    ok = True
    for prev, nxt in zip(present, present[1:]):
        if maxes[prev] > mins[nxt]:
            ok = False
            rep.errors.append(
                f"Ordem temporal violada: max({prev})={maxes[prev]} > min({nxt})={mins[nxt]}"
            )
    rep.temporal_order_ok = ok


def _check_ratios(
    rep: LeakageReport,
    expected: tuple[float, float, float],
    tolerance: float,
) -> None:
    exp_train, exp_val, exp_test = expected
    got = rep.ratios
    deltas = {
        "train": abs(got.get("train", 0) - exp_train),
        "val": abs(got.get("val", 0) - exp_val),
        "test": abs(got.get("test", 0) - exp_test),
    }
    for split, delta in deltas.items():
        if delta > tolerance:
            rep.warnings.append(
                f"Proporção de {split} fora da tolerância: "
                f"obtido={got.get(split, 0):.3f} esperado={expected[['train','val','test'].index(split)]:.3f}"
            )
