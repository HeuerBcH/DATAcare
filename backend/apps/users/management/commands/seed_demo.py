"""
Management command: seed_demo
Creates demo users and sample visits for demonstration purposes.

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --patients 50
    python manage.py seed_demo --reset   (clears existing demo data first)
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.users.models import User
from apps.patients.models import Visit


DEMO_USERS = [
    {"username": "admin",  "first_name": "Admin",    "last_name": "DATAcare",   "email": "admin@datacare.local",  "role": "admin",               "is_staff": True, "is_superuser": True},
    {"username": "gestor", "first_name": "Carlos",   "last_name": "Mendes",     "email": "gestor@datacare.local", "role": "gestor",              "is_staff": False, "is_superuser": False},
    {"username": "acs1",   "first_name": "Maria",    "last_name": "Silva",      "email": "acs1@datacare.local",   "role": "acs",                 "is_staff": False, "is_superuser": False},
    {"username": "acs2",   "first_name": "João",     "last_name": "Santos",     "email": "acs2@datacare.local",   "role": "acs",                 "is_staff": False, "is_superuser": False},
    {"username": "medico", "first_name": "Ana",      "last_name": "Ferreira",   "email": "medico@datacare.local", "role": "profissional_saude",  "is_staff": False, "is_superuser": False},
]

PASSWORD = "datacare123"

SYMPTOM_KEYS = [
    "FEBRE", "MIALGIA", "CEFALEIA", "EXANTEMA", "VOMITO", "NAUSEA",
    "DOR_COSTAS", "CONJUNTVIT", "ARTRITE", "ARTRALGIA", "PETEQUIA_N",
    "LEUCOPENIA", "LACO", "DOR_RETRO", "TOSSE", "GARGANTA", "DISPNEIA",
    "DESC_RESP", "DIARREIA", "FADIGA",
]

COMORBIDITY_KEYS = [
    "DIABETES", "HEMATOLOG", "HEPATOPAT", "RENAL",
    "HIPERTENSA", "ACIDO_PEPT", "AUTO_IMUNE",
]

DISEASE_PROFILES = {
    "dengue":      {"FEBRE": 0.95, "CEFALEIA": 0.85, "MIALGIA": 0.80, "DOR_RETRO": 0.75, "ARTRALGIA": 0.60, "EXANTEMA": 0.50, "VOMITO": 0.40, "PETEQUIA_N": 0.20},
    "chikungunya": {"FEBRE": 0.90, "ARTRALGIA": 0.95, "ARTRITE": 0.80, "EXANTEMA": 0.60, "CEFALEIA": 0.50, "MIALGIA": 0.55, "CONJUNTVIT": 0.35},
    "zika":        {"EXANTEMA": 0.90, "FEBRE": 0.70, "ARTRALGIA": 0.65, "CONJUNTVIT": 0.55, "CEFALEIA": 0.45},
    "influenza":   {"FEBRE": 0.95, "TOSSE": 0.90, "MIALGIA": 0.80, "FADIGA": 0.75, "CEFALEIA": 0.60, "GARGANTA": 0.55, "DISPNEIA": 0.30},
}

BAIRROS = [
    "Centro", "Boa Vista", "Santo Antônio", "Vila Nova", "Jardim das Flores",
    "Cohab", "Várzea", "Caxangá", "Torre", "Madalena", "Encruzilhada",
]

NAMES = [
    "Ana Lima", "Bruno Costa", "Carla Souza", "Diego Alves", "Elena Martins",
    "Felipe Gomes", "Gabriela Rocha", "Henrique Nunes", "Isabela Carvalho",
    "Jonas Ferreira", "Karla Mendes", "Lucas Teixeira", "Marina Oliveira",
    "Nicolas Santos", "Olívia Pereira", "Paulo Ramos", "Queila Barbosa",
    "Rafael Castro", "Sabrina Azevedo", "Tiago Correia", "Úrsula Moreira",
    "Vinícius Ribeiro", "Wanda Freitas", "Xavier Pinto", "Yasmin Duarte",
]


def _random_symptoms(disease: str) -> dict:
    profile = DISEASE_PROFILES.get(disease, {})
    symptoms = {}
    for key in SYMPTOM_KEYS:
        prob = profile.get(key, 0.10)
        symptoms[key] = 1 if random.random() < prob else 0
    return symptoms


def _random_comorbidities(age: int) -> dict:
    base = 0.05 + (0.15 if age > 50 else 0)
    return {key: 1 if random.random() < base else 0 for key in COMORBIDITY_KEYS}


def _severity_from_symptoms(symptoms: dict, comorbidities: dict, age: int) -> str:
    alarm = symptoms.get("PETEQUIA_N", 0) + symptoms.get("LEUCOPENIA", 0) + symptoms.get("LACO", 0)
    n_comorbidities = sum(comorbidities.values())
    if alarm >= 2 or (n_comorbidities >= 2 and age >= 60):
        return "alto"
    if alarm == 1 or n_comorbidities >= 1 or age >= 60:
        return "medio"
    return "baixo"


class Command(BaseCommand):
    help = "Cria usuários e visitas de demonstração para o DATAcare."

    def add_arguments(self, parser):
        parser.add_argument("--patients", type=int, default=180)
        parser.add_argument("--reset", action="store_true", help="Remove visitas existentes antes de criar")

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = Visit.objects.all().delete()
            self.stdout.write(f"  Removidas {deleted} visitas existentes.")
            User.objects.filter(username__in=[u["username"] for u in DEMO_USERS]).delete()
        elif Visit.objects.exists():
            self.stdout.write("  Dados já existem — seed ignorado. Use --reset para recriar.")
            return

        # Create users
        created_users = []
        for data in DEMO_USERS:
            username = data["username"]
            user, created = User.objects.get_or_create(username=username)
            if created or options["reset"]:
                user.first_name = data["first_name"]
                user.last_name = data["last_name"]
                user.email = data["email"]
                user.role = data["role"]
                user.is_staff = data["is_staff"]
                user.is_superuser = data["is_superuser"]
                user.set_password(PASSWORD)
                user.save()
                self.stdout.write(f"  Usuário criado: {username}")
            else:
                self.stdout.write(f"  Usuário já existe: {username}")
            created_users.append(user)

        acs_users = [u for u in created_users if u.role == "acs"]
        diseases = list(DISEASE_PROFILES.keys())
        n = options["patients"]

        visits = []
        for i in range(n):
            disease = random.choice(diseases)
            age = random.randint(5, 80)
            sex = random.choice(["M", "F"])
            symptoms = _random_symptoms(disease)
            comorbidities = _random_comorbidities(age)
            severity = _severity_from_symptoms(symptoms, comorbidities, age)
            days_ago = random.randint(0, 90)

            visits.append(Visit(
                patient_name=random.choice(NAMES),
                patient_age=age,
                patient_sex=sex,
                bairro=random.choice(BAIRROS),
                symptoms=symptoms,
                comorbidities=comorbidities,
                predicted_disease=disease,
                predicted_severity=severity,
                disease_probabilities={d: round(random.uniform(0.05, 0.85), 3) for d in diseases},
                severity_probabilities={"baixo": 0.5, "medio": 0.3, "alto": 0.2},
                model_available=True,
                acs=random.choice(acs_users) if acs_users else None,
                created_at=timezone.now() - timedelta(days=days_ago),
            ))

        Visit.objects.bulk_create(visits)

        self.stdout.write(self.style.SUCCESS(
            f"\nSeed concluído: {len(DEMO_USERS)} usuários | {n} visitas criadas.\n"
            f"Senha de todos os usuários: {PASSWORD}\n"
            f"Usuários: {', '.join(u['username'] for u in DEMO_USERS)}"
        ))
