"""
Dashboard statistics aggregator — operational data only (DB visits).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _operational_stats() -> dict[str, Any]:
    """Aggregate stats from Django Visit records."""
    from apps.patients.models import Visit
    from django.db.models import Count
    from django.utils import timezone

    week_ago = timezone.now() - timedelta(days=7)
    try:
        total_visits   = Visit.objects.count()
        visits_week    = Visit.objects.filter(created_at__gte=week_ago).count()
        high_risk      = Visit.objects.filter(predicted_severity="alto").count()
        active_alerts  = Visit.objects.filter(
            predicted_severity="alto",
            created_at__gte=timezone.now() - timedelta(days=3)
        ).count()

        disease_distribution = dict(
            Visit.objects.values("predicted_disease")
            .annotate(n=Count("id"))
            .values_list("predicted_disease", "n")
        )
        disease_distribution.pop("unknown", None)

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
            "total_visits":        total_visits,
            "visits_week":         visits_week,
            "high_risk":           high_risk,
            "active_alerts":       active_alerts,
            "disease_distribution": disease_distribution,
            "recent_alerts":       recent_alerts,
        }
    except Exception as exc:
        logger.error("DB stats error: %s", exc)
        return {
            "total_visits": 0, "visits_week": 0, "high_risk": 0,
            "active_alerts": 0, "disease_distribution": {}, "recent_alerts": [],
        }


def get_dashboard_stats() -> dict[str, Any]:
    """Returns the full stats payload for GET /api/v1/dashboard/stats/."""
    ops = _operational_stats()
    return {
        "total_visits_week":    ops["visits_week"],
        "total_visits":         ops["total_visits"],
        "high_risk_count":      ops["high_risk"],
        "active_alerts":        ops["active_alerts"],
        "disease_distribution": ops["disease_distribution"],
    }


def get_trend_data() -> list[dict]:
    """Returns trend data for GET /api/v1/dashboard/trends/ from DB visits."""
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
        logger.error("Trend error: %s", exc)
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
