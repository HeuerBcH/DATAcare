from django.contrib import admin
from .models import Patient, PatientVitals


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user', 'cpf', 'date_of_birth', 'gender', 'blood_type', 'created_at')
    list_filter = ('gender', 'blood_type', 'created_at')
    search_fields = ('user__username', 'user__email', 'cpf')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'age')
    
    fieldsets = (
        ('Informações do Usuário', {
            'fields': ('user',)
        }),
        ('Dados Pessoais', {
            'fields': ('cpf', 'date_of_birth', 'age', 'gender', 'blood_type')
        }),
        ('Contato e Endereço', {
            'fields': ('address', 'emergency_contact', 'emergency_phone')
        }),
        ('Informações Médicas', {
            'fields': ('medical_history', 'allergies')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PatientVitals)
class PatientVitalsAdmin(admin.ModelAdmin):
    list_display = ('patient', 'blood_pressure_systolic', 'blood_pressure_diastolic', 'heart_rate', 'temperature', 'measured_at')
    list_filter = ('measured_at', 'patient')
    search_fields = ('patient__user__username', 'patient__cpf')
    ordering = ('-measured_at',)
    readonly_fields = ('measured_at', 'bmi')
    
    fieldsets = (
        ('Paciente', {
            'fields': ('patient',)
        }),
        ('Pressão Arterial', {
            'fields': ('blood_pressure_systolic', 'blood_pressure_diastolic')
        }),
        ('Medidas', {
            'fields': ('heart_rate', 'temperature', 'weight', 'height', 'bmi')
        }),
        ('Glicose e Observações', {
            'fields': ('blood_glucose', 'notes')
        }),
        ('Data de Medição', {
            'fields': ('measured_at',),
            'classes': ('collapse',)
        }),
    )
