"""Modelos do domínio de triagem da Atenção Primária à Saúde (ACS).

Diferente de ``apps.patients`` (portal clínico, onde Patient == User logado),
aqui o paciente é uma pessoa acompanhada em visita domiciliar pelo Agente
Comunitário de Saúde (ACS) e NÃO precisa de conta no sistema. Este app é o
coração do MVP: alimenta o modelo de ML, o dashboard e os alertas.
"""
from datetime import date

from django.conf import settings
from django.db import models


class Patient(models.Model):
    """Pessoa acompanhada pela APS, cadastrada pelo ACS durante as visitas."""

    GENDER_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('O', 'Outro'),
    ]

    full_name = models.CharField('Nome completo', max_length=200)
    birth_date = models.DateField('Data de nascimento')
    gender = models.CharField('Gênero', max_length=1, choices=GENDER_CHOICES)
    phone = models.CharField('Telefone', max_length=20, blank=True)
    address = models.TextField('Endereço', blank=True)
    cpf = models.CharField('CPF', max_length=11, blank=True, null=True, unique=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_patients',
        verbose_name='Cadastrado por (ACS)',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Paciente (APS)'
        verbose_name_plural = 'Pacientes (APS)'
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.cpf or "sem CPF"})'

    @property
    def age(self):
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )


class Symptom(models.Model):
    """Catálogo de sintomas coletáveis na triagem."""

    name = models.CharField('Sintoma', max_length=80, unique=True)
    is_respiratory = models.BooleanField('Respiratório', default=False)

    class Meta:
        verbose_name = 'Sintoma'
        verbose_name_plural = 'Sintomas'
        ordering = ['name']

    def __str__(self):
        return self.name


class Comorbidity(models.Model):
    """Catálogo de comorbidades (condições crônicas)."""

    name = models.CharField('Comorbidade', max_length=80, unique=True)
    is_critical = models.BooleanField('Crítica', default=False)

    class Meta:
        verbose_name = 'Comorbidade'
        verbose_name_plural = 'Comorbidades'
        ordering = ['name']

    def __str__(self):
        return self.name


class Visit(models.Model):
    """Visita domiciliar / triagem registrada pelo ACS — unidade central de dados."""

    RISK_CHOICES = [
        ('baixo', 'Baixo risco'),
        ('medio', 'Médio risco'),
        ('alto', 'Alto risco'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='visits',
        verbose_name='Paciente',
    )
    acs = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visits',
        verbose_name='ACS responsável',
    )
    visit_date = models.DateField('Data da visita', default=date.today)
    medications = models.TextField('Medicações em uso', blank=True)
    notes = models.TextField('Observações', blank=True)
    comorbidities = models.ManyToManyField(
        Comorbidity,
        blank=True,
        related_name='visits',
        verbose_name='Comorbidades',
    )

    # Resultado da predição de risco (preenchido pelo modelo de ML).
    risk_level = models.CharField(
        'Nível de risco', max_length=10, choices=RISK_CHOICES, blank=True
    )
    risk_score = models.FloatField('Score de risco (0-100)', null=True, blank=True)
    model_version = models.CharField('Versão do modelo', max_length=50, blank=True)
    predicted_at = models.DateTimeField('Previsto em', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Visita / Triagem'
        verbose_name_plural = 'Visitas / Triagens'
        ordering = ['-visit_date', '-created_at']
        indexes = [
            models.Index(fields=['-visit_date']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['patient', '-visit_date']),
        ]

    def __str__(self):
        risco = self.get_risk_level_display() if self.risk_level else 'sem risco'
        return f'Visita de {self.patient.full_name} em {self.visit_date} ({risco})'


class VisitSymptom(models.Model):
    """Sintoma relatado numa visita, com severidade e duração."""

    SEVERITY_CHOICES = [
        (1, 'Muito leve'),
        (2, 'Leve'),
        (3, 'Moderado'),
        (4, 'Grave'),
        (5, 'Muito grave'),
    ]

    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        related_name='visit_symptoms',
        verbose_name='Visita',
    )
    symptom = models.ForeignKey(
        Symptom,
        on_delete=models.CASCADE,
        related_name='visit_symptoms',
        verbose_name='Sintoma',
    )
    severity = models.PositiveSmallIntegerField(
        'Severidade', choices=SEVERITY_CHOICES, default=3
    )
    duration_days = models.PositiveIntegerField('Duração (dias)', default=1)

    class Meta:
        verbose_name = 'Sintoma da visita'
        verbose_name_plural = 'Sintomas da visita'
        unique_together = [('visit', 'symptom')]

    def __str__(self):
        return f'{self.symptom.name} (severidade {self.severity})'


class Alert(models.Model):
    """Alerta inteligente gerado por regras sobre as triagens (HU-10)."""

    SEVERITY_CHOICES = [
        ('info', 'Informativo'),
        ('warning', 'Atenção'),
        ('critical', 'Crítico'),
    ]
    TYPE_CHOICES = [
        ('high_risk', 'Paciente de alto risco'),
        ('symptom_spike', 'Pico de sintomas'),
        ('no_followup', 'Acompanhamento em atraso'),
        ('cluster', 'Concentração de casos'),
    ]

    alert_type = models.CharField('Tipo', max_length=20, choices=TYPE_CHOICES)
    severity = models.CharField(
        'Severidade', max_length=10, choices=SEVERITY_CHOICES, default='warning'
    )
    title = models.CharField('Título', max_length=160)
    message = models.TextField('Mensagem')
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts',
        verbose_name='Paciente',
    )
    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts',
        verbose_name='Visita',
    )
    # Chave única que evita alertas duplicados para a mesma situação (HU-10).
    dedup_key = models.CharField('Chave de deduplicação', max_length=200, unique=True)
    is_resolved = models.BooleanField('Resolvido', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_resolved', '-created_at']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        return f'[{self.get_severity_display()}] {self.title}'
