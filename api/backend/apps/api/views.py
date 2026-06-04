from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from apps.users.models import User
from apps.patients.models import Patient, PatientVitals
from apps.predictions.models import PredictionModel, Prediction, PredictionFeedback
from apps.predictions.services import calculate_risk_score, get_risk_level

from .serializers import (
    UserSerializer, UserDetailSerializer, UserCreateSerializer,
    PatientSerializer, PatientDetailSerializer, PatientCreateUpdateSerializer,
    PatientVitalsSerializer, PatientVitalsCreateSerializer,
    PredictionModelSerializer, PredictionSerializer, PredictionDetailSerializer,
    PredictionFeedbackSerializer
)


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
    pagination_class = None
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
        
        risk_score = calculate_risk_score(latest_vitals)

        prediction = Prediction.objects.create(
            patient=patient,
            model=model,
            risk_level=get_risk_level(risk_score),
            probability=risk_score,
            prediction_data={
                'blood_pressure': f"{latest_vitals.blood_pressure_systolic}/{latest_vitals.blood_pressure_diastolic}",
                'heart_rate': latest_vitals.heart_rate,
                'temperature': latest_vitals.temperature,
                'bmi': latest_vitals.bmi,
            },
            clinical_notes='Predição gerada automaticamente com base nos últimos sinais vitais.',
        )

        serializer = PredictionDetailSerializer(prediction)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
