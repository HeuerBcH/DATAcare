from django.urls import path
from . import views

app_name = 'predictions'

urlpatterns = [
    path('list/', views.prediction_list_view, name='prediction_list'),
    path('<int:prediction_id>/', views.prediction_detail_view, name='prediction_detail'),
    path('run/', views.prediction_run_view, name='prediction_run'),
    path('generate/', views.prediction_generate_view, name='prediction_generate'),
]
