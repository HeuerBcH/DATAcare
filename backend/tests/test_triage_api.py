import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.triage.models import Comorbidity, Symptom

User = get_user_model()
PWD = "pass12345"


@pytest.fixture
def acs(db):
    return User.objects.create_user(username="acs_test", password=PWD, role="acs")


@pytest.fixture
def gestor(db):
    return User.objects.create_user(username="gestor_test", password=PWD, role="gestor")


@pytest.fixture
def catalog(db):
    Symptom.objects.create(name="Febre")
    Symptom.objects.create(name="Falta de ar", is_respiratory=True)
    Comorbidity.objects.create(name="Diabetes", is_critical=True)


def auth_client(user):
    client = APIClient()
    res = client.post(
        "/api/v1/auth/login/", {"username": user.username, "password": PWD}, format="json"
    )
    client.credentials(HTTP_AUTHORIZATION="Bearer " + res.data["access"])
    return client


@pytest.mark.django_db
def test_login_returns_tokens(acs):
    res = APIClient().post(
        "/api/v1/auth/login/", {"username": "acs_test", "password": PWD}, format="json"
    )
    assert res.status_code == 200
    assert "access" in res.data and res.data["user"]["role"] == "acs"


@pytest.mark.django_db
def test_login_invalid_credentials(acs):
    res = APIClient().post(
        "/api/v1/auth/login/", {"username": "acs_test", "password": "errada"}, format="json"
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_unauthenticated_is_rejected():
    assert APIClient().get("/api/v1/triage/visits/").status_code == 401


@pytest.mark.django_db
def test_create_triage_predicts_risk(acs, catalog):
    client = auth_client(acs)
    payload = {
        "patient": {"full_name": "Idoso Grave", "birth_date": "1945-01-01", "gender": "M"},
        "symptoms": [
            {"name": "Falta de ar", "severity": 5, "duration_days": 3},
            {"name": "Febre", "severity": 4, "duration_days": 2},
        ],
        "comorbidities": ["Diabetes"],
    }
    res = client.post("/api/v1/triage/visits/", payload, format="json")
    assert res.status_code == 201
    assert res.data["risk_level"] in {"baixo", "medio", "alto"}
    assert res.data["risk_score"] is not None
    assert res.data["patient_name"] == "Idoso Grave"


@pytest.mark.django_db
def test_dashboard_is_gestor_only(acs, gestor):
    assert auth_client(acs).get("/api/v1/triage/visits/dashboard/").status_code == 403
    res = auth_client(gestor).get("/api/v1/triage/visits/dashboard/")
    assert res.status_code == 200
    assert "risk_distribution" in res.data
