from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from apps.patients.models import Patient
from .models import Prediction, PredictionModel


@login_required
def prediction_list_view(request):
    """List predictions for the current user."""
    try:
        patient = request.user.patient
        predictions = patient.predictions.all()
    except Patient.DoesNotExist:
        messages.error(request, 'Você não tem um perfil de paciente.')
        predictions = []
    
    return render(request, 'predictions/prediction_list.html', {
        'predictions': predictions
    })


@login_required
def prediction_detail_view(request, prediction_id):
    """Display prediction details."""
    prediction = get_object_or_404(Prediction, id=prediction_id)
    
    # Check permissions
    if request.user != prediction.patient.user and request.user.role not in ['healthcare', 'admin']:
        messages.error(request, 'Você não tem permissão para acessar esta página.')
        return render(request, 'error.html', {'message': 'Acesso Negado'}, status=403)
    
    return render(request, 'predictions/prediction_detail.html', {
        'prediction': prediction
    })


@login_required
def prediction_run_view(request):
    """Run prediction for current user."""
    try:
        patient = request.user.patient
    except Patient.DoesNotExist:
        messages.error(request, 'Você não tem um perfil de paciente.')
        return render(request, 'error.html', {'message': 'Perfil de Paciente Não Encontrado'}, status=404)
    
    # Get latest vitals
    latest_vitals = patient.vitals.first()
    if not latest_vitals:
        messages.error(request, 'Nenhum sinal vital registrado. Por favor, registre seus sinais vitais primeiro.')
        return render(request, 'error.html', {'message': 'Sinais Vitais Não Encontrados'}, status=404)
    
    # Get active prediction models
    active_models = PredictionModel.objects.filter(is_active=True)
    
    return render(request, 'predictions/run_prediction.html', {
        'patient': patient,
        'latest_vitals': latest_vitals,
        'models': active_models
    })


@login_required
@require_http_methods(["POST"])
def prediction_generate_view(request):
    """Generate a new prediction (simulated)."""
    try:
        patient = request.user.patient
    except Patient.DoesNotExist:
        messages.error(request, 'Você não tem um perfil de paciente.')
        return render(request, 'error.html', {'message': 'Perfil de Paciente Não Encontrado'}, status=404)
    
    model_id = request.POST.get('model_id')
    model = get_object_or_404(PredictionModel, id=model_id, is_active=True)
    
    # Get latest vitals
    latest_vitals = patient.vitals.first()
    if not latest_vitals:
        messages.error(request, 'Nenhum sinal vital registrado.')
        return render(request, 'error.html', {'message': 'Sinais Vitais Não Encontrados'}, status=404)
    
    # Simulate prediction (replace with actual ML model call)
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
        clinical_notes=f"Predição gerada automaticamente baseada nos últimos sinais vitais."
    )
    
    messages.success(request, 'Predição gerada com sucesso!')
    return render(request, 'predictions/prediction_result.html', {
        'prediction': prediction
    })


def calculate_risk_score(vitals):
    """
    Calculate risk score based on vitals.
    This is a simplified example - replace with actual ML model call.
    """
    score = 0
    
    # Blood pressure scoring
    if vitals.blood_pressure_systolic >= 180 or vitals.blood_pressure_diastolic >= 120:
        score += 40
    elif vitals.blood_pressure_systolic >= 140 or vitals.blood_pressure_diastolic >= 90:
        score += 20
    
    # Heart rate scoring
    if vitals.heart_rate >= 120 or vitals.heart_rate <= 40:
        score += 20
    
    # Temperature scoring
    if vitals.temperature >= 38.5 or vitals.temperature <= 35:
        score += 15
    
    # BMI scoring
    bmi = vitals.bmi
    if bmi > 40 or bmi < 16:
        score += 15
    elif bmi > 35 or bmi < 18.5:
        score += 10
    
    return min(score, 100)


def get_risk_level(score):
    """Determine risk level based on score."""
    if score >= 80:
        return 'critical'
    elif score >= 60:
        return 'high'
    elif score >= 40:
        return 'medium'
    else:
        return 'low'
