# DATAcare Django Backend

> Backend com Django MVT para DATAcare — Saúde Digital + ML para APS

## Estrutura

```
backend/
├── manage.py              # Django CLI
├── init_django.py         # Script de inicialização
├── config/               
│   ├── settings.py        # Configurações Django
│   ├── urls.py            # URLs raiz
│   └── wsgi.py            # WSGI application
├── apps/                 
│   ├── users/             # Autenticação e usuários
│   ├── patients/          # Dados de pacientes
│   ├── predictions/       # Resultados de ML
│   └── api/               # Endpoints REST
├── templates/             # Templates HTML (MVT)
├── static/                # CSS, JS estático
├── staticfiles/           # Arquivos estáticos coletados
├── media/                 # Upload de mídia
└── logs/                  # Logs da aplicação
```

## Setup Local

### 1. Preparar Ambiente

```powershell
# Criar virtual environment
py -3.12 -m venv .venv

# Ativar
.\.venv\Scripts\Activate.ps1

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configurar Banco de Dados

```powershell
# Usar PostgreSQL (recomendado)
# ou SQLite para desenvolvimento

# No arquivo .env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=datacare_db
DB_USER=datacare_user
DB_PASSWORD=sua_senha
DB_HOST=localhost
DB_PORT=5432
```

### 3. Executar Setup

```powershell
cd backend
python init_django.py
```

### 4. Criar Superusuário

```powershell
python manage.py createsuperuser
```

### 5. Rodar Servidor

```powershell
python manage.py runserver 0.0.0.0:8000
```

Acesse: http://localhost:8000/admin

## Endpoints da API

### Autenticação

```
POST /api/v1/users/                    # Registrar
POST /api/v1/users/me/                 # Meu perfil
GET  /api/v1/users/{id}/               # Detalhes do usuário
PATCH /api/v1/users/{id}/              # Atualizar perfil
```

### Pacientes

```
GET    /api/v1/patients/               # Listar (healthcare only)
GET    /api/v1/patients/me/            # Meu perfil
GET    /api/v1/patients/{id}/          # Detalhes
POST   /api/v1/patients/               # Criar perfil
PATCH  /api/v1/patients/{id}/          # Atualizar
```

### Sinais Vitais

```
GET    /api/v1/patients/{id}/vitals/       # Listar
POST   /api/v1/patients/{id}/vitals/       # Registrar
GET    /api/v1/patients/{id}/vitals/{id}/  # Detalhes
```

### Predições

```
GET    /api/v1/predictions/            # Listar minhas predições
GET    /api/v1/predictions/{id}/       # Detalhes
POST   /api/v1/predictions/generate/   # Gerar predição
```

### Modelos de ML

```
GET  /api/v1/prediction-models/        # Listar modelos ativos
```

## Modelos de Dados

### User (Custom)
- Estende Django User
- Campos: role, phone, cpf, profile_image, bio

### Patient
- user (OneToOne com User)
- cpf, date_of_birth, gender, blood_type
- address, medical_history, allergies
- emergency_contact

### PatientVitals
- patient (FK com Patient)
- Pressão arterial (sistólica/diastólica)
- heart_rate, temperature, weight, height
- blood_glucose, BMI (calculado)

### Prediction
- patient (FK com Patient)
- model (FK com PredictionModel)
- risk_level, probability
- prediction_data (JSON), clinical_notes

### PredictionModel
- name, description, model_type
- version, accuracy, is_active

## Admin Django

URL: http://localhost:8000/admin

Usuário padrão: `admin`
Senha padrão: `admin123` (mude em produção!)

## Testes

```powershell
# Rodar testes
pytest tests/ -v

# Com cobertura
pytest --cov=apps tests/
```

## Docker

```powershell
# Build
docker-compose build

# Rodar
docker-compose up

# Criar superuser (necessário)
docker-compose exec backend python backend/manage.py createsuperuser
```

## Integração com Frontend React

O frontend acessa a API via `VITE_API_URL`:

```javascript
// src/config/api.js
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

## Variáveis de Ambiente

Veja [.env.example](../.env.example):

```
DEBUG=True
SECRET_KEY=sua-chave-secreta
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=django.db.backends.postgresql
DB_NAME=datacare_db
...
```

## Troubleshooting

### Erro: "psycopg2 not found"
```powershell
pip install psycopg2-binary
```

### Erro: "No such table"
```powershell
python manage.py migrate
```

### Erro: CORS
Verifique `CORS_ALLOWED_ORIGINS` em settings.py

### Erro: Static files não carregam
```powershell
python manage.py collectstatic --noinput
```

## Logs

Logs salvos em `logs/django.log`

Configure em `config/settings.py` na seção `LOGGING`.

## Performance

- Cache com Redis (opcional)
- Database indexing em campos frequentes
- Pagination (20 itens/página por padrão)
- DjangoFilterBackend para filtros

## Segurança

- ✓ CORS configurado
- ✓ Token authentication
- ✓ CSRF protection
- ✓ Password validation
- ✓ SQL injection prevention (ORM)
- ⚠ Ativar HTTPS em produção
- ⚠ Usar variáveis de ambiente para secrets

## Links Úteis

- [Django Docs](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [PostgreSQL](https://www.postgresql.org/)
- [Docker](https://docs.docker.com/)

## Contribuindo

1. Criar branch: `git checkout -b feature/sua-feature`
2. Commit: `git commit -am 'Add feature'`
3. Push: `git push origin feature/sua-feature`
4. PR com descrição

## Licença

Por definir

---

**Desenvolvido para CESAR School — Projeto 6, Grupo 13**
