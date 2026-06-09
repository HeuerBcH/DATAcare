from django.db import models
from django.conf import settings


User = settings.AUTH_USER_MODEL


class Patient(models.Model):
    """
    Patient model to store patient information.
    """
    GENDER_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('O', 'Outro'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='patient',
        verbose_name='Usuário'
    )
    cpf = models.CharField(
        max_length=11,
        unique=True,
        verbose_name='CPF'
    )
    date_of_birth = models.DateField(
        verbose_name='Data de Nascimento'
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        verbose_name='Gênero'
    )
    blood_type = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        verbose_name='Tipo Sanguíneo'
    )
    address = models.TextField(
        verbose_name='Endereço'
    )
    medical_history = models.TextField(
        blank=True,
        null=True,
        verbose_name='Histórico Médico'
    )
    allergies = models.TextField(
        blank=True,
        null=True,
        verbose_name='Alergias'
    )
    emergency_contact = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Contato de Emergência'
    )
    emergency_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Telefone de Emergência'
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
        verbose_name = 'Paciente'
        verbose_name_plural = 'Pacientes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.cpf})"
    
    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class PatientVitals(models.Model):
    """
    Record patient vital signs.
    """
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='vitals',
        verbose_name='Paciente'
    )
    blood_pressure_systolic = models.IntegerField(
        verbose_name='Pressão Sistólica (mmHg)'
    )
    blood_pressure_diastolic = models.IntegerField(
        verbose_name='Pressão Diastólica (mmHg)'
    )
    heart_rate = models.IntegerField(
        verbose_name='Frequência Cardíaca (bpm)'
    )
    temperature = models.FloatField(
        verbose_name='Temperatura (°C)'
    )
    weight = models.FloatField(
        verbose_name='Peso (kg)'
    )
    height = models.FloatField(
        verbose_name='Altura (cm)'
    )
    blood_glucose = models.FloatField(
        blank=True,
        null=True,
        verbose_name='Glicose (mg/dL)'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observações'
    )
    measured_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Medido em'
    )
    
    class Meta:
        verbose_name = 'Sinais Vitais'
        verbose_name_plural = 'Sinais Vitais'
        ordering = ['-measured_at']
        indexes = [
            models.Index(fields=['-measured_at']),
            models.Index(fields=['patient', '-measured_at']),
        ]
    
    def __str__(self):
        return f"Vitals for {self.patient.user.username} on {self.measured_at}"
    
    @property
    def bmi(self):
        """Calculate BMI."""
        height_m = self.height / 100
        return round(self.weight / (height_m ** 2), 2)


class Visit(models.Model):
    """
    ACS field visit / triagem record.
    Stores symptom data, demographics, and ML prediction results.
    Lightweight — does not require a User account per patient.
    """
    DISEASE_CHOICES = [
        ('dengue', 'Dengue'),
        ('chikungunya', 'Chikungunya'),
        ('zika', 'Zika'),
        ('influenza', 'Influenza'),
        ('unknown', 'Desconhecida'),
    ]
    SEVERITY_CHOICES = [
        ('baixo', 'Baixo Risco'),
        ('medio', 'Médio Risco'),
        ('alto', 'Alto Risco'),
    ]
    SEX_CHOICES = [('M', 'Masculino'), ('F', 'Feminino')]

    # Patient info (not linked to User — quick triagem)
    patient_name = models.CharField(max_length=200, verbose_name='Nome do Paciente')
    patient_age = models.PositiveSmallIntegerField(verbose_name='Idade')
    patient_sex = models.CharField(max_length=1, choices=SEX_CHOICES, default='F', verbose_name='Sexo')
    bairro = models.CharField(max_length=100, blank=True, default='', verbose_name='Bairro')

    # Symptom / comorbidity snapshot (SINAN-compatible keys, 0/1)
    symptoms = models.JSONField(default=dict, verbose_name='Sintomas')
    comorbidities = models.JSONField(default=dict, verbose_name='Comorbidades')

    # ML prediction results
    predicted_disease = models.CharField(
        max_length=20, choices=DISEASE_CHOICES, blank=True, default='unknown',
        verbose_name='Doença Predita'
    )
    predicted_severity = models.CharField(
        max_length=10, choices=SEVERITY_CHOICES, blank=True, default='baixo',
        verbose_name='Gravidade Predita'
    )
    disease_probabilities = models.JSONField(default=dict, verbose_name='Prob. Doença')
    severity_probabilities = models.JSONField(default=dict, verbose_name='Prob. Gravidade')
    model_available = models.BooleanField(default=False, verbose_name='Modelo Disponível')

    # ACS who registered
    acs = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='visits', verbose_name='ACS Responsável'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Visita / Triagem'
        verbose_name_plural = 'Visitas / Triagens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['predicted_severity', '-created_at']),
            models.Index(fields=['predicted_disease']),
        ]

    def __str__(self):
        return f"{self.patient_name} — {self.predicted_disease} ({self.predicted_severity})"
