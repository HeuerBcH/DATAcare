from django.db import models
from apps.patients.models import Patient


class PredictionModel(models.Model):
    """
    Model registry for ML models.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nome do Modelo'
    )
    description = models.TextField(
        verbose_name='Descrição'
    )
    model_type = models.CharField(
        max_length=50,
        verbose_name='Tipo de Modelo',
        help_text='Ex: XGBoost, RandomForest, Neural Network'
    )
    version = models.CharField(
        max_length=20,
        verbose_name='Versão'
    )
    accuracy = models.FloatField(
        blank=True,
        null=True,
        verbose_name='Acurácia'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Atualizado em'
    )
    
    class Meta:
        verbose_name = 'Modelo de Predição'
        verbose_name_plural = 'Modelos de Predição'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} (v{self.version})"


class Prediction(models.Model):
    """
    Store predictions for patients.
    """
    RISK_LEVEL_CHOICES = [
        ('low', 'Baixo Risco'),
        ('medium', 'Médio Risco'),
        ('high', 'Alto Risco'),
        ('critical', 'Risco Crítico'),
    ]
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='predictions',
        verbose_name='Paciente'
    )
    model = models.ForeignKey(
        PredictionModel,
        on_delete=models.PROTECT,
        related_name='predictions',
        verbose_name='Modelo'
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        verbose_name='Nível de Risco'
    )
    probability = models.FloatField(
        verbose_name='Probabilidade (%)',
        help_text='Valor entre 0 e 100'
    )
    prediction_data = models.JSONField(
        verbose_name='Dados da Predição',
        default=dict
    )
    clinical_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observações Clínicas'
    )
    recommended_actions = models.TextField(
        blank=True,
        null=True,
        verbose_name='Ações Recomendadas'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )
    
    class Meta:
        verbose_name = 'Predição'
        verbose_name_plural = 'Predições'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['patient', '-created_at']),
            models.Index(fields=['risk_level']),
        ]
    
    def __str__(self):
        return f"{self.patient.user.username} - {self.get_risk_level_display()} ({self.model.name})"


class PredictionFeedback(models.Model):
    """
    Collect feedback on predictions for model improvement.
    """
    FEEDBACK_CHOICES = [
        ('accurate', 'Precisa'),
        ('inaccurate', 'Imprecisa'),
        ('partial', 'Parcialmente Precisa'),
    ]
    
    prediction = models.OneToOneField(
        Prediction,
        on_delete=models.CASCADE,
        related_name='feedback',
        verbose_name='Predição'
    )
    feedback = models.CharField(
        max_length=20,
        choices=FEEDBACK_CHOICES,
        verbose_name='Retorno'
    )
    healthcare_professional = models.CharField(
        max_length=200,
        verbose_name='Profissional de Saúde'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observações'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )
    
    class Meta:
        verbose_name = 'Retorno de Predição'
        verbose_name_plural = 'Retornos de Predições'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.prediction.patient.user.username} - {self.get_feedback_display()}"
