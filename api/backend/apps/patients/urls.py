from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('list/', views.patient_list_view, name='patient_list'),
    path('<int:patient_id>/', views.patient_detail_view, name='patient_detail'),
    path('vitals/add/', views.vitals_add_view, name='vitals_add'),
    path('vitals/history/', views.vitals_history_view, name='vitals_history'),
]
