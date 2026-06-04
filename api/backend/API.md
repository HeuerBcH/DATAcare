# DATAcare REST API Documentation

> **Atualizado em:** branch `feature/hu03-hu04` — autenticação migrada para JWT

## Base URL

```
http://localhost:8000/api/v1/
```

## Authentication — JWT (Bearer Token)

Todas as rotas protegidas exigem o header:
```
Authorization: Bearer <access_token>
```

O `access_token` é obtido em `/api/v1/auth/login/` ou `/api/v1/auth/register/`.
Duração: **8 horas**. Use `/api/v1/auth/refresh/` para renovar sem novo login.

## Perfis de usuário (roles)

| Role | Descrição | Acesso principal |
|---|---|---|
| `gestor` | Gestor/Coordenador de UBS | Dashboard, alertas, indicadores, configuração |
| `acs` | Agente Comunitário de Saúde | Formulários de visita, dados de pacientes atribuídos |
| `profissional_saude` | Médico, enfermeiro, etc. | Prontuários, triagem, sinais vitais |
| `admin` | Administrador do sistema | Acesso irrestrito |

## Endpoints de Autenticação

### POST /api/v1/auth/register/

Cria usuário e retorna tokens imediatamente.

Request:
```json
{
  "username": "gestor_ubs01",
  "email": "gestor@ubs.recife.pe.gov.br",
  "password": "DataCare@2024",
  "password_confirm": "DataCare@2024",
  "first_name": "Ana",
  "last_name": "Souza",
  "role": "gestor",
  "phone": "81999990000"
}
```

Response (201):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhb...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhb...",
  "user": {
    "id": 1,
    "username": "gestor_ubs01",
    "email": "gestor@ubs.recife.pe.gov.br",
    "role": "gestor",
    "role_display": "Gestor/Coordenador de UBS"
  }
}
```

### POST /api/v1/auth/login/

Request:
```json
{
  "username": "gestor_ubs01",
  "password": "DataCare@2024"
}
```

Response (200): mesmo formato do register.

### POST /api/v1/auth/refresh/

```json
{ "refresh": "<refresh_token>" }
```

Response (200): `{ "access": "<novo_access_token>" }`

### POST /api/v1/auth/logout/

```
Authorization: Bearer <access_token>
```
```json
{ "refresh": "<refresh_token>" }
```

Invalida o refresh token (blacklist). Response (200): `{ "detail": "Logout realizado com sucesso." }`

### GET /api/v1/auth/me/

```
Authorization: Bearer <access_token>
```

Retorna dados do usuário autenticado.

## Endpoints

### Users — POST /api/v1/users/ (criar via API, sem token)

Request:
```json
{
  "username": "usuario1",
  "email": "user@example.com",
  "password": "senha123",
  "password_confirm": "senha123",
  "first_name": "João",
  "last_name": "Silva",
  "role": "profissional_saude"
}
```

Response (201):
```json
{
  "id": 1,
  "username": "usuario1",
  "email": "user@example.com",
  "first_name": "João",
  "last_name": "Silva",
  "role": "patient",
  "created_at": "2024-05-20T10:30:00Z"
}
```

#### Get Profile
```
GET /users/me/
Authorization: Token <token>
```

Response (200):
```json
{
  "id": 1,
  "username": "usuario1",
  "email": "user@example.com",
  "first_name": "João",
  "last_name": "Silva",
  "role": "patient",
  "phone": "11999999999",
  "cpf": "12345678901",
  "bio": "Bio",
  "created_at": "2024-05-20T10:30:00Z",
  "updated_at": "2024-05-20T10:30:00Z"
}
```

#### Update Profile
```
PATCH /users/{id}/
Authorization: Token <token>
```

Request:
```json
{
  "first_name": "João",
  "last_name": "Silva",
  "phone": "11999999999",
  "bio": "Atualizado"
}
```

### 🏥 Patients

#### List (healthcare professionals only)
```
GET /patients/
Authorization: Token <token>
```

Response (200):
```json
[
  {
    "id": 1,
    "user": {
      "id": 1,
      "username": "usuario1",
      "email": "user@example.com",
      "first_name": "João",
      "last_name": "Silva"
    },
    "cpf": "12345678901",
    "date_of_birth": "1990-05-20",
    "age": 34,
    "gender": "M",
    "blood_type": "O+",
    "address": "Rua X, 123",
    "medical_history": "...",
    "allergies": "Penicilina",
    "emergency_contact": "Maria Silva",
    "emergency_phone": "11999999998",
    "latest_vitals": {
      "id": 1,
      "blood_pressure_systolic": 120,
      "blood_pressure_diastolic": 80,
      "heart_rate": 72,
      "temperature": 36.5,
      "weight": 75.0,
      "height": 180.0,
      "blood_glucose": 100,
      "bmi": 23.15,
      "measured_at": "2024-05-20T10:30:00Z"
    }
  }
]
```

#### Get My Profile
```
GET /patients/me/
Authorization: Token <token>
```

#### Create Patient Profile
```
POST /patients/
Authorization: Token <token>
```

Request:
```json
{
  "cpf": "12345678901",
  "date_of_birth": "1990-05-20",
  "gender": "M",
  "blood_type": "O+",
  "address": "Rua X, 123",
  "medical_history": "Hipertensão",
  "allergies": "Penicilina",
  "emergency_contact": "Maria Silva",
  "emergency_phone": "11999999998"
}
```

#### Update Patient Profile
```
PATCH /patients/{id}/
Authorization: Token <token>
```

### 📊 Patient Vitals

#### List Vitals
```
GET /patients/{patient_id}/vitals/
Authorization: Token <token>
```

Response (200):
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "blood_pressure_systolic": 120,
      "blood_pressure_diastolic": 80,
      "heart_rate": 72,
      "temperature": 36.5,
      "weight": 75.0,
      "height": 180.0,
      "blood_glucose": 100,
      "bmi": 23.15,
      "notes": "Normal",
      "measured_at": "2024-05-20T10:30:00Z"
    }
  ]
}
```

#### Add Vitals
```
POST /patients/{patient_id}/vitals/
Authorization: Token <token>
```

Request:
```json
{
  "blood_pressure_systolic": 120,
  "blood_pressure_diastolic": 80,
  "heart_rate": 72,
  "temperature": 36.5,
  "weight": 75.0,
  "height": 180.0,
  "blood_glucose": 100,
  "notes": "Normal"
}
```

Response (201):
```json
{
  "id": 2,
  "blood_pressure_systolic": 120,
  "blood_pressure_diastolic": 80,
  "heart_rate": 72,
  "temperature": 36.5,
  "weight": 75.0,
  "height": 180.0,
  "blood_glucose": 100,
  "bmi": 23.15,
  "notes": "Normal",
  "measured_at": "2024-05-20T11:00:00Z"
}
```

#### Get Vitals Details
```
GET /patients/{patient_id}/vitals/{vitals_id}/
Authorization: Token <token>
```

### 🤖 Predictions

#### List My Predictions
```
GET /predictions/
Authorization: Token <token>
```

Response (200):
```json
[
  {
    "id": 1,
    "patient": 1,
    "patient_name": "João Silva",
    "model": 1,
    "model_name": "XGBoost Risk v1",
    "risk_level": "high",
    "risk_level_display": "Alto Risco",
    "probability": 75.5,
    "prediction_data": {
      "blood_pressure": "140/90",
      "heart_rate": 85
    },
    "clinical_notes": "Paciente em risco elevado",
    "recommended_actions": "Agendar consulta urgente",
    "created_at": "2024-05-20T10:30:00Z"
  }
]
```

#### Get Prediction Details
```
GET /predictions/{id}/
Authorization: Token <token>
```

Response (200):
```json
{
  "id": 1,
  "patient": 1,
  "patient_name": "João Silva",
  "model": 1,
  "model_name": "XGBoost Risk v1",
  "risk_level": "high",
  "risk_level_display": "Alto Risco",
  "probability": 75.5,
  "prediction_data": {...},
  "clinical_notes": "...",
  "recommended_actions": "...",
  "feedback": {
    "id": 1,
    "feedback": "accurate",
    "feedback_display": "Precisa",
    "healthcare_professional": "Dr. Silva",
    "notes": "Observações",
    "created_at": "2024-05-20T11:00:00Z"
  },
  "created_at": "2024-05-20T10:30:00Z"
}
```

#### Generate Prediction
```
POST /predictions/generate/
Authorization: Token <token>
```

Request:
```json
{
  "model_id": 1
}
```

Response (201):
```json
{
  "id": 2,
  "patient": 1,
  "patient_name": "João Silva",
  "model": 1,
  "model_name": "XGBoost Risk v1",
  "risk_level": "medium",
  "risk_level_display": "Médio Risco",
  "probability": 55.0,
  "prediction_data": {...},
  "clinical_notes": "Predição gerada automaticamente",
  "recommended_actions": null,
  "created_at": "2024-05-20T11:00:00Z"
}
```

### 🧠 Prediction Models

#### List Active Models
```
GET /prediction-models/
Authorization: Token <token>
```

Response (200):
```json
[
  {
    "id": 1,
    "name": "XGBoost Risk v1",
    "description": "Modelo XGBoost para predição de risco",
    "model_type": "XGBoost",
    "version": "1.0.0",
    "accuracy": 0.92,
    "is_active": true,
    "created_at": "2024-05-20T09:00:00Z"
  }
]
```

## Error Responses

### 400 Bad Request
```json
{
  "field_name": ["Error message"]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Server error"
}
```

## Status Codes

| Code | Significado |
|------|-------------|
| 200 | OK |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Server Error |

## Filtering, Searching & Ordering

### Filter Predictions by Risk Level
```
GET /predictions/?risk_level=high
```

### Search Patients by Name
```
GET /patients/?search=João
```

### Order by Date (descending)
```
GET /predictions/?ordering=-created_at
```

## Pagination

Default: 20 items per page

```
GET /patients/?page=2
```

Response:
```json
{
  "count": 50,
  "next": "http://localhost:8000/api/v1/patients/?page=3",
  "previous": "http://localhost:8000/api/v1/patients/?page=1",
  "results": [...]
}
```

## Examples with JavaScript/Fetch

### Login e salvar tokens
```javascript
const res = await fetch('http://localhost:8000/api/v1/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'gestor_ubs01', password: 'DataCare@2024' })
});
const { access, refresh, user } = await res.json();
localStorage.setItem('access_token', access);
localStorage.setItem('refresh_token', refresh);
```

### Chamada autenticada com JWT
```javascript
const token = localStorage.getItem('access_token');
const response = await fetch('http://localhost:8000/api/v1/auth/me/', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

## Rate Limiting

Sem limite atualmente. Pode ser adicionado em produção.

## CORS

Configurado para:
- http://localhost:3000
- http://localhost:5173
- http://127.0.0.1:3000
- http://127.0.0.1:5173

Modifique em `.env` se necessário.

## Versionamento

Atual: `v1`

Future versions: `/api/v2/`, `/api/v3/`, etc.

## Schema

Acesse a documentação interativa em:
```
http://localhost:8000/api/schema/
```

---

**Documentação da API REST - DATAcare**
