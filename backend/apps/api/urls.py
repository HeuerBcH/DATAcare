from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    UserViewSet, PatientViewSet, PatientVitalsViewSet,
    PredictionModelViewSet, PredictionViewSet,
    VisitViewSet,
    PredictView,
    DashboardStatsView, DashboardTrendsView, DashboardAlertsView,
)

app_name = 'api'

router = SimpleRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'prediction-models', PredictionModelViewSet, basename='prediction-model')
router.register(r'predictions', PredictionViewSet, basename='prediction')
router.register(r'visits', VisitViewSet, basename='visit')

urlpatterns = [
    path('', include(router.urls)),

    # Nested patient vitals
    path('patients/<int:patient_pk>/vitals/', PatientVitalsViewSet.as_view({
        'get': 'list', 'post': 'create'
    }), name='patient-vitals-list'),
    path('patients/<int:patient_pk>/vitals/<int:pk>/', PatientVitalsViewSet.as_view({
        'get': 'retrieve'
    }), name='patient-vitals-detail'),

    # ML prediction endpoint
    path('predict/', PredictView.as_view(), name='predict'),

    # Dashboard data endpoints
    path('dashboard/stats/',  DashboardStatsView.as_view(),  name='dashboard-stats'),
    path('dashboard/trends/', DashboardTrendsView.as_view(), name='dashboard-trends'),
    path('dashboard/alerts/', DashboardAlertsView.as_view(), name='dashboard-alerts'),
]
