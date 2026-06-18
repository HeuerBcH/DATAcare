from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from apps.users.models import User
from apps.patients.models import Patient, PatientVitals, Visit
from apps.predictions.models import PredictionModel, Prediction, PredictionFeedback

from .serializers import (
    UserSerializer, UserDetailSerializer, UserCreateSerializer,
    PatientSerializer, PatientDetailSerializer, PatientCreateUpdateSerializer,
    PatientVitalsSerializer, PatientVitalsCreateSerializer,
    PredictionModelSerializer, PredictionSerializer, PredictionDetailSerializer,
    PredictionFeedbackSerializer,
    VisitSerializer, VisitCreateSerializer, PredictInputSerializer,
)
from .predict_service import predict_full
from .dashboard import get_dashboard_stats, get_trend_data, get_recent_alerts


# ============= User ViewSets =============
class UserViewSet(viewsets.ViewSet):
    """API endpoint for user management."""
    
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def list(self, request):
        """List all users (admin only)."""
        if request.user.role != 'admin':
            return Response({'detail': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)
        
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get user details."""
        user = get_object_or_404(User, pk=pk)
        
        if request.user != user and request.user.role != 'admin':
            return Response({'detail': 'Sem permissão'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = UserDetailSerializer(user)
        return Response(serializer.data)
    
    def create(self, request):
        """Create a new user."""
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, pk=None):
        """Update user profile."""
        user = get_object_or_404(User, pk=pk)
        
        if request.user != user and request.user.role != 'admin':
            return Response({'detail': 'Sem permissão'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user details."""
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)


# ============= Patient ViewSets =============
class PatientViewSet(viewsets.ViewSet):
    """API endpoint for patient management."""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """List patients (healthcare professionals only)."""
        if request.user.role not in ['profissional_saude', 'admin']:
            return Response({'detail': 'Sem permissão'}, status=status.HTTP_403_FORBIDDEN)
        
        patients = Patient.objects.all()
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get patient details."""
        patient = get_object_or_404(Patient, pk=pk)
        
        if request.user != patient.user and request.user.role not in ['profissional_saude', 'admin']:
            return Response({'detail': 'Sem permissão'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PatientDetailSerializer(patient)
        return Response(serializer.data)
    
    def create(self, request):
        """Create patient profile."""
        serializer = PatientCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            patient = serializer.save(user=request.user)
            return Response(PatientSerializer(patient).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, pk=None):
        """Update patient profile."""
        patient = get_object_or_404(Patient, pk=pk)
        
        if request.user != patient.user and request.user.role != 'admin':
            return Response({'detail': 'Sem permissão'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PatientCreateUpdateSerializer(patient, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(PatientSerializer(patient).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's patient profile."""
        try:
            patient = request.user.patient
            serializer = PatientDetailSerializer(patient)
            return Response(serializer.data)
        except Patient.DoesNotExist:
            return Response({'detail': 'Perfil de paciente não encontrado'}, status=status.HTTP_404_NOT_FOUND)


class PatientVitalsViewSet(viewsets.ViewSet):
    """API endpoint for patient vitals."""
    permission_classes = [IsAuthenticated]
    
    def list(self, request, patient_pk=None):
        """List vitals for a patient."""
        patient = get_object_or_404(Patient, pk=patient_pk)
        
        if request.user != patient.user and request.user.role not in ['profissional_saude', 'admin']:
            return Response({'detail': 'Sem permissão'}, status=status.HTTP_403_FORBIDDEN)
        
        vitals = patient.vitals.all()
        serializer = PatientVitalsSerializer(vitals, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, patient_pk=None, pk=None):
        """Get vitals details."""
        patient = get_object_or_404(Patient, pk=patient_pk)
        vitals = get_object_or_404(PatientVitals, pk=pk, patient=patient)
        
        if request.user != patient.user and request.user.role not in ['profissional_saude', 'admin']:
            return Response({'detail': 'Sem permissão'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PatientVitalsSerializer(vitals)
        return Response(serializer.data)
    
    def create(self, request, patient_pk=None):
        """Create vitals record."""
        patient = get_object_or_404(Patient, pk=patient_pk)
        
        if request.user != patient.user and request.user.role != 'admin':
            return Response({'detail': 'Sem permissão'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PatientVitalsCreateSerializer(data=request.data)
        if serializer.is_valid():
            vitals = serializer.save(patient=patient)
            return Response(PatientVitalsSerializer(vitals).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============= Prediction ViewSets =============
class PredictionModelViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for prediction models."""
    permission_classes = [IsAuthenticated]
    queryset = PredictionModel.objects.filter(is_active=True)
    serializer_class = PredictionModelSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'accuracy']


class PredictionViewSet(viewsets.ViewSet):
    """API endpoint for predictions."""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """List predictions for current user."""
        try:
            patient = request.user.patient
            predictions = patient.predictions.all()
            serializer = PredictionSerializer(predictions, many=True)
            return Response(serializer.data)
        except Patient.DoesNotExist:
            return Response({'detail': 'Perfil de paciente não encontrado'}, status=status.HTTP_404_NOT_FOUND)
    
    def retrieve(self, request, pk=None):
        """Get prediction details."""
        prediction = get_object_or_404(Prediction, pk=pk)
        
        if request.user != prediction.patient.user and request.user.role not in ['profissional_saude', 'admin']:
            return Response({'detail': 'Sem permissão'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PredictionDetailSerializer(prediction)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a new prediction."""
        try:
            patient = request.user.patient
        except Patient.DoesNotExist:
            return Response({'detail': 'Perfil de paciente não encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        model_id = request.data.get('model_id')
        model = get_object_or_404(PredictionModel, pk=model_id, is_active=True)
        
        # Get latest vitals
        latest_vitals = patient.vitals.first()
        if not latest_vitals:
            return Response({'detail': 'Nenhum sinal vital registrado'}, status=status.HTTP_400_BAD_REQUEST)

        features = {
            'age_years': float(patient.age),
            'sex_M': 1.0 if patient.gender == 'M' else 0.0,
            'FEBRE': 1.0 if latest_vitals.temperature > 37.5 else 0.0,
        }
        result = predict_full(features)
        if result is None:
            return Response(
                {'detail': 'Modelos ML não disponíveis. Execute o pipeline de treinamento.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        severity = result['severity']['predicted_class']
        severity_to_risk = {'baixo': 'low', 'medio': 'medium', 'alto': 'high'}
        risk_level = severity_to_risk.get(severity, 'medium')
        risk_score = round(max(result['severity']['probabilities'].values()) * 100, 1)

        prediction = Prediction.objects.create(
            patient=patient,
            model=model,
            risk_level=risk_level,
            probability=risk_score,
            prediction_data={
                'blood_pressure': f"{latest_vitals.blood_pressure_systolic}/{latest_vitals.blood_pressure_diastolic}",
                'heart_rate': latest_vitals.heart_rate,
                'predicted_disease': result['disease']['predicted_class'],
                'disease_probabilities': result['disease']['probabilities'],
                'severity_probabilities': result['severity']['probabilities'],
            }
        )
        
        serializer = PredictionDetailSerializer(prediction)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


def get_risk_level_from_score(score):
    if score >= 80:
        return 'critical'
    elif score >= 60:
        return 'high'
    elif score >= 40:
        return 'medium'
    return 'low'


# ============= Visit / Triagem ViewSet =============

class VisitViewSet(viewsets.ViewSet):
    """
    POST /api/v1/visits/ — ACS registers a triagem visit.
    Calls ML models automatically and stores prediction alongside symptoms.
    GET  /api/v1/visits/ — list visits (gestor/admin see all; ACS sees own).
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        if request.user.role in ('gestor', 'admin', 'profissional_saude'):
            qs = Visit.objects.all()
        else:
            qs = Visit.objects.filter(acs=request.user)
        serializer = VisitSerializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = VisitCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        visit = serializer.save(acs=request.user)

        # Build feature vector for ML
        features = {
            'age_years': float(visit.patient_age),
            'sex_M': 1.0 if visit.patient_sex == 'M' else 0.0,
        }
        features.update({k: float(v) for k, v in visit.symptoms.items()})
        features.update({k: float(v) for k, v in visit.comorbidities.items()})

        result = predict_full(features)
        if result:
            visit.predicted_disease = result['disease']['predicted_class']
            visit.predicted_severity = result['severity']['predicted_class']
            visit.disease_probabilities = result['disease']['probabilities']
            visit.severity_probabilities = result['severity']['probabilities']
            visit.model_available = True
        else:
            visit.model_available = False
        visit.save()

        return Response(VisitSerializer(visit).data, status=status.HTTP_201_CREATED)


# ============= Standalone Predict Endpoint =============

class PredictView(APIView):
    """
    POST /api/v1/predict/
    Body: {"features": {"FEBRE": 1, "ARTRITE": 1, "age_years": 45, ...}}
    Returns: {disease: {...}, severity: {...}}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PredictInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        result = predict_full(serializer.validated_data['features'])
        if result is None:
            return Response(
                {'detail': 'Modelos ML não disponíveis. Execute o pipeline de treinamento.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(result)


# ============= Dashboard Endpoints =============

class DashboardStatsView(APIView):
    """GET /api/v1/dashboard/stats/ — KPIs + disease distribution."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_dashboard_stats())


class DashboardTrendsView(APIView):
    """GET /api/v1/dashboard/trends/ — time-series trend data."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_trend_data())


class DashboardAlertsView(APIView):
    """GET /api/v1/dashboard/alerts/ — recent high-risk visits."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_recent_alerts())
