from django.contrib import admin
from .models import PredictionModel, Prediction, PredictionFeedback


@admin.register(PredictionModel)
class PredictionModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'model_type', 'version', 'accuracy', 'is_active', 'created_at')
    list_filter = ('model_type', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'model', 'risk_level', 'probability', 'created_at')
    list_filter = ('risk_level', 'model', 'created_at')
    search_fields = ('patient__user__username', 'patient__cpf')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(PredictionFeedback)
class PredictionFeedbackAdmin(admin.ModelAdmin):
    list_display = ('prediction', 'feedback', 'healthcare_professional', 'created_at')
    list_filter = ('feedback', 'created_at')
    search_fields = ('prediction__patient__user__username', 'healthcare_professional')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
