from django.contrib import admin

from .models import Alert, Comorbidity, Patient, Symptom, Visit, VisitSymptom


class VisitSymptomInline(admin.TabularInline):
    model = VisitSymptom
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'cpf', 'gender', 'age', 'phone', 'registered_by', 'created_at')
    list_filter = ('gender',)
    search_fields = ('full_name', 'cpf', 'phone')


@admin.register(Symptom)
class SymptomAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_respiratory')
    list_filter = ('is_respiratory',)
    search_fields = ('name',)


@admin.register(Comorbidity)
class ComorbidityAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_critical')
    list_filter = ('is_critical',)
    search_fields = ('name',)


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('patient', 'visit_date', 'acs', 'risk_level', 'risk_score', 'created_at')
    list_filter = ('risk_level', 'visit_date')
    search_fields = ('patient__full_name', 'patient__cpf')
    inlines = [VisitSymptomInline]
    filter_horizontal = ('comorbidities',)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'alert_type', 'severity', 'patient', 'is_resolved', 'created_at')
    list_filter = ('severity', 'alert_type', 'is_resolved')
    search_fields = ('title', 'message')
