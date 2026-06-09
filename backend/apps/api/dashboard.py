"""
Dashboard statistics aggregator.

Data sources (in priority order):
1. SINAN/SRAG parquet files — epidemiological data (disease distribution, trends)
2. Visit DB records — operational data (this week's visits, risk counts, alerts)

Designed to degrade gracefully: if parquets are missing or DB is empty,
returns zeros rather than crashing.
"""
from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PIPELINE_DIR = Path(__file__).resolve().parents[3] / "data_pipeline"
_INTERIM_DIR = _PIPELINE_DIR / "data" / "interim"

DISEASE_DATASETS = {
    "dengue":      _INTERIM_DIR / "sinan_dengue.parquet",
    "chikungunya": _INTERIM_DIR / "sinan_chikungunya.parquet",
    "zika":        _INTERIM_DIR / "sinan_zika.parquet",
    "influenza":   _INTERIM_DIR / "srag_influenza.parquet",
}


# ---------------------------------------------------------------------------
# Parquet helpers
# ---------------------------------------------------------------------------

def _read_parquet(path: Path):
    """Load parquet file or return None if unavailable."""
    try:
        import pandas as pd
        if not path.exists():
            return None
        return pd.read_parquet(path, columns=["DT_NOTIFIC"])
    except Exception as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None


def _disease_distribution_from_parquets() -> dict[str, int] | None:
    """
    Count total confirmed cases per disease from SINAN parquets.
    Returns None if no parquets are available.
    """
    try:
        distribution: dict[str, int] = {}
        any_found = False
        for disease, path in DISEASE_DATASETS.items():
            df = _read_parquet(path)
            if df is not None:
                distribution[disease] = len(df)
                any_found = True
            else:
                distribution[disease] = 0
        return distribution if any_found else None
    except Exception as exc:
        logger.error("Error computing disease distribution: %s", exc)
        return None


def _trend_from_parquets() -> list[dict] | None:
    """
    Monthly case counts by disease from SINAN parquets.
    Returns list of {month, dengue, chikungunya, zika, influenza} or None.
    """
    try:
        import pandas as pd

        pieces: dict[str, "pd.Series"] = {}
        any_found = False

        for disease, path in DISEASE_DATASETS.items():
            try:
                if not path.exists():
                    continue
                df = pd.read_parquet(path, columns=["DT_NOTIFIC"])
                if df.empty or "DT_NOTIFIC" not in df.columns:
                    continue
                df["DT_NOTIFIC"] = pd.to_datetime(df["DT_NOTIFIC"], errors="coerce")
                df = df.dropna(subset=["DT_NOTIFIC"])
                if df.empty:
                    continue
                monthly = df.set_index("DT_NOTIFIC").resample("ME").size()
                pieces[disease] = monthly
                any_found = True
            except Exception as exc:
                logger.warning("Trend error for %s: %s", disease, exc)

        if not any_found:
            return None

        # Align all series to a common monthly index
        all_months = sorted(set().union(*[s.index for s in pieces.values()]))
        result = []
        for month in all_months[-24:]:  # last 24 months of data available
            row = {
                "date": month.strftime("%b/%Y"),
                "dengue":      int(pieces.get("dengue",      pd.Series(dtype=int)).get(month, 0)),
                "chikungunya": int(pieces.get("chikungunya", pd.Series(dtype=int)).get(month, 0)),
                "zika":        int(pieces.get("zika",        pd.Series(dtype=int)).get(month, 0)),
                "influenza":   int(pieces.get("influenza",   pd.Series(dtype=int)).get(month, 0)),
            }
            result.append(row)
        return result

    except Exception as exc:
        logger.error("Error computing trends: %s", exc)
        return None


# ---------------------------------------------------------------------------
# DB helpers (Visit model)
# ---------------------------------------------------------------------------

def _operational_stats() -> dict[str, Any]:
    """Aggregate stats from Django Visit records."""
    from apps.patients.models import Visit
    from django.utils import timezone

    week_ago = timezone.now() - timedelta(days=7)
    try:
        visits_week = Visit.objects.filter(created_at__gte=week_ago).count()
        high_risk = Visit.objects.filter(predicted_severity="alto").count()
        active_alerts = Visit.objects.filter(
            predicted_severity="alto",
            created_at__gte=timezone.now() - timedelta(days=3)
        ).count()

        # Disease distribution from DB visits (fallback)
        from django.db.models import Count
        db_disease_dist = dict(
            Visit.objects.values("predicted_disease")
            .annotate(n=Count("id"))
            .values_list("predicted_disease", "n")
        )
        db_disease_dist.pop("unknown", None)

        # Recent alerts
        recent_alerts = list(
            Visit.objects.filter(predicted_severity="alto")
            .order_by("-created_at")[:10]
            .values(
                "id", "patient_name", "predicted_severity",
                "predicted_disease", "bairro", "created_at",
            )
        )
        for a in recent_alerts:
            if isinstance(a["created_at"], datetime):
                a["created_at"] = a["created_at"].isoformat()

        return {
            "visits_week": visits_week,
            "high_risk": high_risk,
            "active_alerts": active_alerts,
            "db_disease_dist": db_disease_dist,
            "recent_alerts": recent_alerts,
        }
    except Exception as exc:
        logger.error("DB stats error: %s", exc)
        return {
            "visits_week": 0, "high_risk": 0, "active_alerts": 0,
            "db_disease_dist": {}, "recent_alerts": [],
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_dashboard_stats() -> dict[str, Any]:
    """
    Returns the full stats payload consumed by GET /api/v1/dashboard/stats/.
    Merges parquet-based epidemiological data with DB operational data.
    """
    ops = _operational_stats()
    parquet_dist = _disease_distribution_from_parquets()

    # Disease distribution: prefer parquets (real SINAN data), fall back to DB
    if parquet_dist:
        disease_distribution = parquet_dist
        data_source = "sinan_parquets"
    elif ops["db_disease_dist"]:
        disease_distribution = {
            "dengue": ops["db_disease_dist"].get("dengue", 0),
            "chikungunya": ops["db_disease_dist"].get("chikungunya", 0),
            "zika": ops["db_disease_dist"].get("zika", 0),
            "influenza": ops["db_disease_dist"].get("influenza", 0),
        }
        data_source = "db_visits"
    else:
        disease_distribution = {"dengue": 0, "chikungunya": 0, "zika": 0, "influenza": 0}
        data_source = "no_data"

    total_cases = sum(disease_distribution.values())

    return {
        "total_visits_week": ops["visits_week"],
        "total_cases": total_cases,
        "high_risk_count": ops["high_risk"],
        "active_alerts": ops["active_alerts"],
        "disease_distribution": disease_distribution,
        "data_source": data_source,
    }


def get_trend_data() -> list[dict]:
    """
    Returns trend data for GET /api/v1/dashboard/trends/.
    Uses SINAN parquets when available, falls back to DB Visit records.
    """
    parquet_trend = _trend_from_parquets()
    if parquet_trend:
        return parquet_trend

    # Fallback: group DB visits by week
    try:
        from apps.patients.models import Visit
        from django.db.models import Count
        from django.db.models.functions import TruncWeek

        rows = (
            Visit.objects.annotate(week=TruncWeek("created_at"))
            .values("week", "predicted_disease")
            .annotate(n=Count("id"))
            .order_by("week")
        )
        grouped: dict[str, dict] = {}
        for row in rows:
            key = row["week"].strftime("%d/%m") if row["week"] else "?"
            if key not in grouped:
                grouped[key] = {"date": key, "dengue": 0, "chikungunya": 0, "zika": 0, "influenza": 0}
            disease = row["predicted_disease"]
            if disease in grouped[key]:
                grouped[key][disease] += row["n"]
        return list(grouped.values())[-30:]
    except Exception as exc:
        logger.error("Trend fallback error: %s", exc)
        return []


def get_recent_alerts() -> list[dict]:
    """Returns recent high-risk visits for GET /api/v1/dashboard/alerts/."""
    try:
        from apps.patients.models import Visit
        alerts = list(
            Visit.objects.filter(predicted_severity__in=["alto", "medio"])
            .order_by("-created_at")[:20]
            .values(
                "id", "patient_name", "predicted_severity",
                "predicted_disease", "bairro", "created_at",
            )
        )
        for a in alerts:
            if isinstance(a["created_at"], datetime):
                a["created_at"] = a["created_at"].isoformat()
        return alerts
    except Exception as exc:
        logger.error("Alerts error: %s", exc)
        return []
