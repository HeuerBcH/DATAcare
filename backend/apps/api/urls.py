from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    UserViewSet, PatientViewSet, PatientVitalsViewSet,
    PredictionModelViewSet, PredictionViewSet
)

app_name = 'api'

router = SimpleRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'prediction-models', PredictionModelViewSet, basename='prediction-model')
router.register(r'predictions', PredictionViewSet, basename='prediction')

urlpatterns = [
    path('', include(router.urls)),
    path('patients/<int:patient_pk>/vitals/', PatientVitalsViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='patient-vitals-list'),
    path('patients/<int:patient_pk>/vitals/<int:pk>/', PatientVitalsViewSet.as_view({
        'get': 'retrieve'
    }), name='patient-vitals-detail'),
]
