from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsGestorOrAdmin, IsUBSStaff

from .models import Alert, Comorbidity, Patient, Symptom, Visit
from .serializers import (
    AlertSerializer,
    ComorbiditySerializer,
    PatientSerializer,
    SymptomSerializer,
    TriageCreateSerializer,
    VisitSerializer,
)
from .services import build_dashboard


class SymptomViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de sintomas (para montar o formulário de triagem)."""

    queryset = Symptom.objects.all()
    serializer_class = SymptomSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class ComorbidityViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de comorbidades."""

    queryset = Comorbidity.objects.all()
    serializer_class = ComorbiditySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsUBSStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["full_name", "cpf", "phone"]
    ordering_fields = ["full_name", "created_at"]

    def perform_create(self, serializer):
        serializer.save(registered_by=self.request.user)


class VisitViewSet(viewsets.ModelViewSet):
    """Visitas/triagens. O ACS vê só as próprias; gestor/admin/profissional veem todas."""

    permission_classes = [IsUBSStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["risk_level", "patient"]
    search_fields = ["patient__full_name", "patient__cpf"]
    ordering_fields = ["visit_date", "risk_score", "created_at"]

    def get_queryset(self):
        qs = Visit.objects.select_related("patient", "acs").prefetch_related(
            "visit_symptoms__symptom", "comorbidities"
        )
        user = self.request.user
        if getattr(user, "role", None) == "acs":
            qs = qs.filter(acs=user)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return TriageCreateSerializer
        return VisitSerializer

    def create(self, request, *args, **kwargs):
        serializer = TriageCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        visit = serializer.save()
        return Response(VisitSerializer(visit).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], permission_classes=[IsGestorOrAdmin])
    def dashboard(self, request):
        """Indicadores agregados para o gestor (HU-09)."""
        return Response(build_dashboard())


class AlertViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Alertas inteligentes (HU-10) — visíveis para gestor/admin."""

    queryset = Alert.objects.select_related("patient", "visit").all()
    serializer_class = AlertSerializer
    permission_classes = [IsGestorOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["severity", "alert_type", "is_resolved"]

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.is_resolved = True
        alert.save(update_fields=["is_resolved"])
        return Response(AlertSerializer(alert).data)
