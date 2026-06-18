# DATAcare — Backend Django

Backend REST com Django 4.2 + DRF + JWT para o DATAcare.

## Estrutura

```
backend/
├── manage.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── users/              # Auth JWT + RBAC + seed_demo
│   ├── patients/           # Visit (triagem) + Patient + PatientVitals
│   ├── predictions/        # Predições (MVT legacy)
│   └── api/                # Endpoints REST + dashboard + predict
├── staticfiles/
├── media/
└── logs/
```

## Setup local

```bash
cd backend
python manage.py migrate
python manage.py seed_demo        # cria usuários e triagens de demo
python manage.py runserver 0.0.0.0:8000
```

> Pré-requisito: venv com `pip install -r ../requirements.txt` e PostgreSQL rodando.
> Consulte [`../documentacoes/RODAR_LOCAL.md`](../documentacoes/RODAR_LOCAL.md) para o guia completo.

## Docker (recomendado)

```bash
docker compose up -d
# seed_demo roda automaticamente no startup do backend
```

## Logins de demonstração

Senha para todos: **`datacare123`**

| Usuário | Papel |
|---------|-------|
| `gestor` | Gestor de UBS |
| `acs1` / `acs2` | Agente Comunitário |
| `medico` | Profissional de Saúde |
| `admin` | Administrador (`/admin`) |

## Endpoints principais

```
# Autenticação
POST  /api/v1/auth/login/
POST  /api/v1/auth/logout/
POST  /api/v1/auth/refresh/
GET   /api/v1/auth/me/

# Triagens (visitas ACS)
GET   /api/v1/visits/
POST  /api/v1/visits/

# Predição ML
POST  /api/v1/predict/

# Dashboard
GET   /api/v1/dashboard/stats/
GET   /api/v1/dashboard/trends/
GET   /api/v1/dashboard/alerts/

# Pacientes e sinais vitais
GET/POST  /api/v1/patients/
GET/POST  /api/v1/patients/{id}/vitals/
```

Documentação interativa: http://localhost:8000/api/schema/

## Testes

```bash
cd backend
pytest -v
```

## Admin Django

http://localhost:8000/admin — login com `admin` / `datacare123`
