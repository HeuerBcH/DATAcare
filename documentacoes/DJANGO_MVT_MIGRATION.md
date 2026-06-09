# Migração de FastAPI para Django MVT

## 📋 Resumo

Este documento descreve a migração completa do backend de **FastAPI** para **Django MVT** (Model-View-Template).

## ❌ O que Foi Removido

- ❌ FastAPI
- ❌ Uvicorn
- ❌ Pydantic models (substituídos por Django models)
- ❌ Async/await (substituído por funções síncronas do Django)

## ✅ O que Foi Adicionado

- ✅ **Django 4.2.8** - Framework web MVT
- ✅ **Django REST Framework** - Para endpoints REST/JSON
- ✅ **PostgreSQL** - Database robusta
- ✅ **Django ORM** - Modelos de dados
- ✅ **Admin Django** - Interface de administração
- ✅ **Autenticação Django** - Sistema de usuários
- ✅ **Templates Bootstrap** - UI básica
- ✅ **CORS** - Integração com React frontend

## 🏗️ Estrutura do Novo Backend

```
backend/
├── config/
│   ├── settings.py         # Configurações
│   ├── urls.py             # Rotas raiz
│   └── wsgi.py             # Entry point
├── apps/
│   ├── users/              # Autenticação
│   │   ├── models.py       # User customizado
│   │   ├── views.py        # Views MVT
│   │   ├── urls.py         # URLs
│   │   └── admin.py        # Admin config
│   ├── patients/           # Pacientes
│   │   ├── models.py       # Patient, PatientVitals
│   │   ├── views.py        # Views MVT
│   │   └── ...
│   ├── predictions/        # Predições ML
│   │   ├── models.py       # Prediction, PredictionModel
│   │   ├── views.py        # Views MVT
│   │   └── ...
│   └── api/                # Endpoints REST
│       ├── serializers.py  # DRF serializers
│       ├── views.py        # ViewSets (DRF)
│       └── urls.py         # API URLs
├── templates/              # HTML templates
├── static/                 # CSS, JS estático
├── manage.py               # Django CLI
└── init_django.py          # Setup script
```

## 🔄 Comparativo: FastAPI vs Django MVT

### Modelo de Dados

**FastAPI (Pydantic):**
```python
from pydantic import BaseModel

class PatientCreate(BaseModel):
    cpf: str
    date_of_birth: date
    gender: str
```

**Django MVT (ORM):**
```python
from django.db import models

class Patient(models.Model):
    cpf = models.CharField(max_length=11, unique=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
```

### Endpoints REST

**FastAPI:**
```python
from fastapi import FastAPI

@app.get("/patients/")
async def list_patients():
    return []

@app.post("/patients/")
async def create_patient(patient: PatientCreate):
    return {}
```

**Django MVT (DRF):**
```python
from rest_framework import viewsets

class PatientViewSet(viewsets.ViewSet):
    def list(self, request):
        patients = Patient.objects.all()
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        serializer = PatientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
```

### Autenticação

**FastAPI:**
```python
from fastapi import Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.get("/protected")
async def protected_route(token: str = Depends(security)):
    return {"token": token}
```

**Django MVT:**
```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_route(request):
    return Response({"user": request.user.username})
```

## 🚀 Como Rodar

### 1. Setup Inicial

```powershell
.\scripts\setup.ps1
```

### 2. Migrations

```powershell
cd backend
python manage.py migrate
```

### 3. Criar Superuser

```powershell
python manage.py createsuperuser
```

### 4. Rodar Servidor

```powershell
python manage.py runserver 0.0.0.0:8000
```

### 5. Acessar

- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000/api/v1/
- **Admin:** http://localhost:8000/admin

## 📚 Endpoints REST

Veja [API.md](API.md) para documentação completa.

### Base URL: `/api/v1/`

```
Users
  GET    /users/           - Listar
  POST   /users/           - Registrar
  GET    /users/me/        - Meu perfil

Patients
  GET    /patients/        - Listar
  POST   /patients/        - Criar
  GET    /patients/me/     - Meu perfil

Vitals
  GET    /patients/{id}/vitals/    - Listar
  POST   /patients/{id}/vitals/    - Registrar

Predictions
  GET    /predictions/     - Minhas predições
  POST   /predictions/generate/ - Gerar

Models
  GET    /prediction-models/ - Listar
```

## 🔐 Autenticação

A API usa **Token Authentication** ou **Session Authentication**.

### Token Authentication

```javascript
// Frontend
const token = localStorage.getItem('auth_token');
fetch('http://localhost:8000/api/v1/users/me/', {
  headers: {
    'Authorization': `Token ${token}`
  }
});
```

### Session Authentication

Usa cookies (CSRF protected).

## 🗄️ Database

### PostgreSQL Setup

```powershell
# Criar database
createdb datacare_db

# Criar usuário
createuser datacare_user
```

### Migrations

```powershell
# Criar nova migration
python manage.py makemigrations

# Aplicar
python manage.py migrate

# Ver status
python manage.py showmigrations
```

## 🧪 Testes

```powershell
# Rodar todos
pytest tests/ -v

# Rodar módulo específico
pytest tests/users/ -v

# Com cobertura
pytest --cov=apps tests/
```

## 🐳 Docker

```powershell
# Build
docker-compose build

# Rodar
docker-compose up

# Logs
docker-compose logs -f backend

# Shell Django
docker-compose exec backend python backend/manage.py shell
```

## 📊 Admin Django

URL: http://localhost:8000/admin

Gerenciar:
- ✓ Usuários e perfis
- ✓ Pacientes e dados
- ✓ Predições
- ✓ Modelos de ML

## ⚙️ Configuração

### Variáveis de Ambiente (.env)

```
DEBUG=True
SECRET_KEY=...
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=datacare_db
DB_USER=datacare_user
DB_PASSWORD=...
CORS_ALLOWED_ORIGINS=http://localhost:3000,...
```

### settings.py

Apps instalados:
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    # ...
    'corsheaders',
    'rest_framework',
    'django_filters',
    'apps.users',
    'apps.patients',
    'apps.predictions',
    'apps.api',
]
```

## 🔄 Integração com Frontend

O frontend React acessa via:

```javascript
const API_URL = 'http://localhost:8000/api/v1/';

// Exemplo: Login
const response = await fetch(`${API_URL}users/`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    username: 'user',
    email: 'user@example.com',
    password: 'senha123'
  })
});
```

## 📈 Performance

- ✓ Database indexing
- ✓ Query optimization (select_related, prefetch_related)
- ✓ Caching com Redis (opcional)
- ✓ Pagination (20 itens/página)
- ✓ Filtering e searching

## 🔒 Segurança

### Implementadas

- ✓ CSRF protection
- ✓ SQL injection prevention (ORM)
- ✓ XSS protection
- ✓ Password hashing (PBKDF2)
- ✓ Rate limiting (via middleware)
- ✓ CORS configuration
- ✓ Token authentication

### To-Do

- ⚠ HTTPS em produção
- ⚠ Environment secrets
- ⚠ 2FA (opcional)
- ⚠ Rate limiting avançado

## 🆘 Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'django'"

```powershell
pip install -r requirements.txt
```

### Erro: "No such table"

```powershell
python manage.py migrate
```

### Erro: CORS issue

Verifique `CORS_ALLOWED_ORIGINS` em `.env`

### Erro: "psycopg2 not found"

```powershell
pip install psycopg2-binary
```

## 📚 Referências

- [Django Docs](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [PostgreSQL](https://www.postgresql.org/)
- [Bootstrap](https://getbootstrap.com/)

## 🎯 Próximos Passos

1. [ ] Integrar modelo de ML real
2. [ ] Implementar cache com Redis
3. [ ] Adicionar logging avançado
4. [ ] Criar testes automatizados
5. [ ] Setup de CI/CD (GitHub Actions)
6. [ ] Deploy em produção

---

**Desenvolvido com Django + DRF + PostgreSQL**
**CESAR School — Projeto 6, Grupo 13**
