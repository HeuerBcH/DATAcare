from rest_framework.routers import DefaultRouter

from .views import (
    AlertViewSet,
    ComorbidityViewSet,
    PatientViewSet,
    SymptomViewSet,
    VisitViewSet,
)

app_name = "triage"

router = DefaultRouter()
router.register("symptoms", SymptomViewSet, basename="triage-symptom")
router.register("comorbidities", ComorbidityViewSet, basename="triage-comorbidity")
router.register("patients", PatientViewSet, basename="triage-patient")
router.register("visits", VisitViewSet, basename="triage-visit")
router.register("alerts", AlertViewSet, basename="triage-alert")

urlpatterns = router.urls
