"""Serviços de domínio da triagem: predição de risco, alertas e indicadores."""
from __future__ import annotations

import logging
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from .models import Alert, Patient, Visit, VisitSymptom

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Predição de risco — integra o modelo de ML (data_pipeline/src/ml)
# ---------------------------------------------------------------------------
def visit_to_record(visit: Visit) -> dict:
    """Monta o registro de entrada do modelo a partir de uma Visit persistida."""
    symptoms = [
        {"name": vs.symptom.name, "severity": vs.severity, "duration_days": vs.duration_days}
        for vs in visit.visit_symptoms.select_related("symptom").all()
    ]
    comorbidities = [c.name for c in visit.comorbidities.all()]
    num_prev = visit.patient.visits.exclude(pk=visit.pk).count()
    return {
        "age": visit.patient.age,
        "gender": visit.patient.gender,
        "symptoms": symptoms,
        "comorbidities": comorbidities,
        "num_previous_visits": num_prev,
    }


def predict_and_store(visit: Visit) -> Visit:
    """Roda o modelo sobre a visita e grava o risco. Nunca quebra o fluxo."""
    try:
        from src.ml.model import predict_risk  # data_pipeline está no sys.path (settings)

        level, score, version = predict_risk(visit_to_record(visit))
        visit.risk_level = level
        visit.risk_score = score
        visit.model_version = version
        visit.predicted_at = timezone.now()
        visit.save(update_fields=["risk_level", "risk_score", "model_version", "predicted_at"])
    except Exception:
        logger.exception("Falha ao prever risco da visita %s", visit.pk)
    return visit


# ---------------------------------------------------------------------------
# Motor de alertas (HU-10)
# ---------------------------------------------------------------------------
def _ensure_alert(dedup_key: str, **defaults):
    """Cria o alerta só se ainda não existir (deduplicação por chave)."""
    obj, created = Alert.objects.get_or_create(dedup_key=dedup_key, defaults=defaults)
    return obj if created else None


def generate_alerts_for_visit(visit: Visit) -> list:
    """Regras disparadas a cada triagem avaliada."""
    created = []
    if visit.risk_level == "alto":
        created.append(
            _ensure_alert(
                f"high_risk:visit:{visit.pk}",
                alert_type="high_risk",
                severity="critical",
                title=f"Alto risco: {visit.patient.full_name}",
                message=(
                    f"A triagem de {visit.visit_date} classificou "
                    f"{visit.patient.full_name} como ALTO risco "
                    f"(score {visit.risk_score}). Priorizar atendimento."
                ),
                patient=visit.patient,
                visit=visit,
            )
        )
    sym = {vs.symptom.name for vs in visit.visit_symptoms.all()}
    if "Falta de ar" in sym and "Febre" in sym:
        created.append(
            _ensure_alert(
                f"resp:visit:{visit.pk}",
                alert_type="symptom_spike",
                severity="warning",
                title=f"Sinal respiratório: {visit.patient.full_name}",
                message="Febre + falta de ar na mesma visita. Avaliar quadro respiratório (SRAG).",
                patient=visit.patient,
                visit=visit,
            )
        )
    return [a for a in created if a]


def scan_followup_alerts(days: int = 30) -> list:
    """Sinaliza pacientes de médio/alto risco sem visita recente."""
    created = []
    cutoff = timezone.now().date() - timedelta(days=days)
    for patient in Patient.objects.all():
        last = patient.visits.order_by("-visit_date").first()
        if last and last.risk_level in ("medio", "alto") and last.visit_date < cutoff:
            alert = _ensure_alert(
                f"no_followup:patient:{patient.pk}:{last.visit_date}",
                alert_type="no_followup",
                severity="warning",
                title=f"Acompanhamento em atraso: {patient.full_name}",
                message=(
                    f"Última triagem em {last.visit_date} "
                    f"({last.get_risk_level_display()}) há mais de {days} dias sem retorno."
                ),
                patient=patient,
                visit=last,
            )
            if alert:
                created.append(alert)
    return created


# ---------------------------------------------------------------------------
# Indicadores do dashboard do gestor (HU-09)
# ---------------------------------------------------------------------------
def build_dashboard() -> dict:
    visits = Visit.objects.all()

    risk_distribution = {lvl: 0 for lvl in ("baixo", "medio", "alto")}
    for row in visits.exclude(risk_level="").values("risk_level").annotate(c=Count("id")):
        risk_distribution[row["risk_level"]] = row["c"]

    top_symptoms = [
        {"name": r["symptom__name"], "count": r["c"]}
        for r in VisitSymptom.objects.values("symptom__name")
        .annotate(c=Count("id"))
        .order_by("-c")[:8]
    ]
    visits_over_time = [
        {"date": r["visit_date"].isoformat(), "count": r["c"]}
        for r in visits.values("visit_date").annotate(c=Count("id")).order_by("visit_date")
    ]
    alerts_qs = Alert.objects.filter(is_resolved=False)
    alerts_by_severity = {
        r["severity"]: r["c"] for r in alerts_qs.values("severity").annotate(c=Count("id"))
    }
    critical_patients = [
        {
            "visit_id": v.pk,
            "patient_name": v.patient.full_name,
            "age": v.patient.age,
            "risk_score": v.risk_score,
            "visit_date": v.visit_date.isoformat(),
        }
        for v in visits.filter(risk_level="alto").select_related("patient").order_by("-visit_date")[:10]
    ]
    return {
        "total_patients": Patient.objects.count(),
        "total_visits": visits.count(),
        "active_alerts": alerts_qs.count(),
        "risk_distribution": risk_distribution,
        "alerts_by_severity": alerts_by_severity,
        "top_symptoms": top_symptoms,
        "visits_over_time": visits_over_time,
        "critical_patients": critical_patients,
    }
