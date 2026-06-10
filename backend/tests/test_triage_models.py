from datetime import date

import pytest

from apps.triage.models import Comorbidity, Patient, Symptom, Visit, VisitSymptom


@pytest.mark.django_db
def test_patient_age_property():
    p = Patient.objects.create(full_name="Maria Teste", birth_date=date(2000, 1, 1), gender="F")
    assert p.age >= 24


@pytest.mark.django_db
def test_visit_relations_and_symptoms():
    patient = Patient.objects.create(full_name="João Teste", birth_date=date(1980, 5, 5), gender="M")
    febre = Symptom.objects.create(name="Febre")
    diabetes = Comorbidity.objects.create(name="Diabetes", is_critical=True)
    visit = Visit.objects.create(patient=patient)
    VisitSymptom.objects.create(visit=visit, symptom=febre, severity=4, duration_days=2)
    visit.comorbidities.add(diabetes)

    assert visit.visit_symptoms.count() == 1
    assert patient.visits.count() == 1
    assert visit.comorbidities.first().is_critical is True


@pytest.mark.django_db
def test_visit_symptom_unique_together():
    patient = Patient.objects.create(full_name="Ana Teste", birth_date=date(1990, 2, 2), gender="F")
    sym = Symptom.objects.create(name="Tosse", is_respiratory=True)
    visit = Visit.objects.create(patient=patient)
    VisitSymptom.objects.create(visit=visit, symptom=sym, severity=3, duration_days=1)
    with pytest.raises(Exception):
        VisitSymptom.objects.create(visit=visit, symptom=sym, severity=2, duration_days=1)
