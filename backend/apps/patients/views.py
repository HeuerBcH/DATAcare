from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .models import Patient, PatientVitals


@login_required
def patient_list_view(request):
    """List all patients (for healthcare professionals)."""
    if request.user.role != 'healthcare' and request.user.role != 'admin':
        messages.error(request, 'Você não tem permissão para acessar esta página.')
        return redirect('users:profile')
    
    patients = Patient.objects.all()
    
    return render(request, 'patients/patient_list.html', {'patients': patients})


@login_required
def patient_detail_view(request, patient_id):
    """Display patient details and vital signs."""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check permissions
    if request.user != patient.user and request.user.role not in ['healthcare', 'admin']:
        messages.error(request, 'Você não tem permissão para acessar esta página.')
        return redirect('users:profile')
    
    vitals = patient.vitals.all()[:10]
    
    return render(request, 'patients/patient_detail.html', {
        'patient': patient,
        'vitals': vitals
    })


@login_required
@require_http_methods(["GET", "POST"])
def vitals_add_view(request):
    """Add patient vital signs."""
    if request.method == 'POST':
        patient = get_object_or_404(Patient, user=request.user)
        
        vitals = PatientVitals.objects.create(
            patient=patient,
            blood_pressure_systolic=int(request.POST.get('blood_pressure_systolic')),
            blood_pressure_diastolic=int(request.POST.get('blood_pressure_diastolic')),
            heart_rate=int(request.POST.get('heart_rate')),
            temperature=float(request.POST.get('temperature')),
            weight=float(request.POST.get('weight')),
            height=float(request.POST.get('height')),
            blood_glucose=float(request.POST.get('blood_glucose')) if request.POST.get('blood_glucose') else None,
            notes=request.POST.get('notes'),
        )
        
        messages.success(request, 'Sinais vitais registrados com sucesso!')
        return redirect('patients:patient_detail', patient_id=patient.id)
    
    try:
        patient = request.user.patient
    except Patient.DoesNotExist:
        messages.error(request, 'Você não tem um perfil de paciente.')
        return redirect('users:profile')
    
    return render(request, 'patients/vitals_add.html', {'patient': patient})


@login_required
def vitals_history_view(request):
    """Display patient vitals history."""
    try:
        patient = request.user.patient
    except Patient.DoesNotExist:
        messages.error(request, 'Você não tem um perfil de paciente.')
        return redirect('users:profile')
    
    vitals = patient.vitals.all()
    
    return render(request, 'patients/vitals_history.html', {
        'patient': patient,
        'vitals': vitals
    })
