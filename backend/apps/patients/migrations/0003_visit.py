# Generated for Visit model (ACS triage records)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('patients', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('patient_name', models.CharField(max_length=200, verbose_name='Nome do Paciente')),
                ('patient_age', models.PositiveSmallIntegerField(verbose_name='Idade')),
                ('patient_sex', models.CharField(choices=[('M', 'Masculino'), ('F', 'Feminino')], default='F', max_length=1, verbose_name='Sexo')),
                ('bairro', models.CharField(blank=True, default='', max_length=100, verbose_name='Bairro')),
                ('symptoms', models.JSONField(default=dict, verbose_name='Sintomas')),
                ('comorbidities', models.JSONField(default=dict, verbose_name='Comorbidades')),
                ('predicted_disease', models.CharField(blank=True, choices=[('dengue', 'Dengue'), ('chikungunya', 'Chikungunya'), ('zika', 'Zika'), ('influenza', 'Influenza'), ('unknown', 'Desconhecida')], default='unknown', max_length=20, verbose_name='Doença Predita')),
                ('predicted_severity', models.CharField(blank=True, choices=[('baixo', 'Baixo Risco'), ('medio', 'Médio Risco'), ('alto', 'Alto Risco')], default='baixo', max_length=10, verbose_name='Gravidade Predita')),
                ('disease_probabilities', models.JSONField(default=dict, verbose_name='Prob. Doença')),
                ('severity_probabilities', models.JSONField(default=dict, verbose_name='Prob. Gravidade')),
                ('model_available', models.BooleanField(default=False, verbose_name='Modelo Disponível')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('acs', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='visits', to=settings.AUTH_USER_MODEL, verbose_name='ACS Responsável')),
            ],
            options={
                'verbose_name': 'Visita / Triagem',
                'verbose_name_plural': 'Visitas / Triagens',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='visit',
            index=models.Index(fields=['-created_at'], name='patients_vi_created_idx'),
        ),
        migrations.AddIndex(
            model_name='visit',
            index=models.Index(fields=['predicted_severity', '-created_at'], name='patients_vi_sev_created_idx'),
        ),
        migrations.AddIndex(
            model_name='visit',
            index=models.Index(fields=['predicted_disease'], name='patients_vi_disease_idx'),
        ),
    ]
