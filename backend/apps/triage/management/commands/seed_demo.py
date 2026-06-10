"""Popula o banco com dados sintéticos para a demonstração.

Cria usuários (gestor/acs/médico/admin), catálogos de sintomas e comorbidades,
pacientes com visitas/triagens, roda a predição de risco em cada visita e gera
os alertas. Uso::

    python manage.py seed_demo --patients 180 --reset
"""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from apps.triage.models import Alert, Comorbidity, Patient, Symptom, Visit, VisitSymptom
from apps.triage.services import (
    generate_alerts_for_visit,
    predict_and_store,
    scan_followup_alerts,
)

User = get_user_model()

DEMO_PASSWORD = "datacare123"


class Command(BaseCommand):
    help = "Popula o banco com dados sintéticos para a demo (usuários, catálogos, pacientes, visitas, alertas)."

    def add_arguments(self, parser):
        parser.add_argument("--patients", type=int, default=180)
        parser.add_argument("--reset", action="store_true", help="Limpa os dados de triagem antes de semear")

    def handle(self, *args, **opts):
        from faker import Faker

        from src.ml.features import COMORBIDITY_CATALOG, SYMPTOM_CATALOG
        from src.ml.synthetic import random_record

        if opts["reset"]:
            Alert.objects.all().delete()
            VisitSymptom.objects.all().delete()
            Visit.objects.all().delete()
            Patient.objects.all().delete()
            self.stdout.write("Dados de triagem anteriores removidos.")

        users = self._seed_users()
        acs_users = [u for u in users if u.role == "acs"]

        sym_map = {
            name: Symptom.objects.get_or_create(name=name, defaults={"is_respiratory": resp})[0]
            for name, resp in SYMPTOM_CATALOG
        }
        com_map = {
            name: Comorbidity.objects.get_or_create(name=name, defaults={"is_critical": crit})[0]
            for name, crit in COMORBIDITY_CATALOG
        }

        rng = random.Random(7)
        fake = Faker("pt_BR")
        Faker.seed(7)

        today = timezone.now().date()
        created_visits = 0

        for _ in range(opts["patients"]):
            base = random_record(rng)
            gender = base["gender"]
            if gender == "M":
                name = fake.name_male()
            elif gender == "F":
                name = fake.name_female()
            else:
                name = fake.name()
            birth = today - timedelta(days=base["age"] * 365 + rng.randint(0, 364))
            patient = Patient.objects.create(
                full_name=name,
                birth_date=birth,
                gender=gender,
                phone=fake.msisdn()[:11],
                address=fake.address().replace("\n", ", "),
                cpf=str(fake.unique.random_int(10000000000, 99999999999)),
                registered_by=rng.choice(acs_users) if acs_users else None,
            )

            for _v in range(rng.choices([1, 2, 3], weights=[60, 28, 12])[0]):
                rec = random_record(rng)
                visit = Visit.objects.create(
                    patient=patient,
                    acs=patient.registered_by or (rng.choice(acs_users) if acs_users else None),
                    visit_date=today - timedelta(days=rng.randint(0, 60)),
                    medications=rng.choice(
                        ["", "", "Losartana 50mg", "Metformina 850mg", "Dipirona se dor"]
                    ),
                    notes="",
                )
                for s in rec["symptoms"]:
                    VisitSymptom.objects.create(
                        visit=visit,
                        symptom=sym_map[s["name"]],
                        severity=s["severity"],
                        duration_days=s["duration_days"],
                    )
                com_objs = [com_map[c] for c in rec["comorbidities"] if c in com_map]
                if com_objs:
                    visit.comorbidities.set(com_objs)

                predict_and_store(visit)
                generate_alerts_for_visit(visit)
                created_visits += 1

        scan_followup_alerts()

        dist = {
            row["risk_level"]: row["c"]
            for row in Visit.objects.exclude(risk_level="")
            .values("risk_level")
            .annotate(c=Count("id"))
        }
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed concluído: {Patient.objects.count()} pacientes, {created_visits} visitas, "
                f"{Alert.objects.count()} alertas. Distribuição de risco: {dist}. "
                f"Logins (senha {DEMO_PASSWORD}): gestor, acs1, acs2, medico, admin."
            )
        )

    def _seed_users(self):
        seeds = [
            ("gestor", "gestor", "Gestora", "UBS Boa Vista", "gestor@datacare.local"),
            ("acs1", "acs", "Ana", "Agente", "acs1@datacare.local"),
            ("acs2", "acs", "Bruno", "Agente", "acs2@datacare.local"),
            ("medico", "profissional_saude", "Carla", "Enfermeira", "medico@datacare.local"),
        ]
        users = []
        for username, role, first, last, email in seeds:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"role": role, "first_name": first, "last_name": last, "email": email},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            users.append(user)

        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "role": "admin",
                "is_staff": True,
                "is_superuser": True,
                "email": "admin@datacare.local",
                "first_name": "Admin",
            },
        )
        if created:
            admin.set_password(DEMO_PASSWORD)
            admin.save()
        return users
