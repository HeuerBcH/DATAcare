# Rodar o DATAcare localmente (MVP)

Guia passo a passo para subir a plataforma na sua máquina, **sem Docker e sem Postgres**
(usa SQLite por padrão). Comandos em **PowerShell (Windows)**; no Linux/macOS troque
`\` por `/` e `.venv\Scripts\python.exe` por `.venv/bin/python`.

> Pré-requisitos: **Python 3.10–3.12** e **Node.js 18+**.
> ⚠️ Django 4.2 não roda no Python 3.13/3.14 — use 3.10–3.12 para o backend.

---

## 1. Backend (Django + ML)

```powershell
# Na raiz do projeto (DATAcare/)
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 1.1 Treinar o modelo de risco (gera o .joblib)

```powershell
$env:PYTHONPATH = "$PWD\data_pipeline"
python -m src.ml.train          # ~10s — salva data_pipeline/models/risk_model.joblib
python -m src.ml.eda            # opcional: gera relatório + gráficos da EDA
```

### 1.2 Criar o banco e popular com dados de demonstração

```powershell
cd backend
python manage.py migrate
python manage.py seed_demo --patients 180 --reset
cd ..
```

O `seed_demo` cria os usuários, os catálogos de sintomas/comorbidades e ~180 pacientes
com visitas e alertas — rodando a predição de risco em cada triagem.

### 1.3 Subir a API

```powershell
python backend\manage.py runserver 127.0.0.1:8000
```

- API: http://127.0.0.1:8000/api/v1/
- Admin Django: http://127.0.0.1:8000/admin/

---

## 2. Frontend (React + Vite)

Em **outro terminal**, na raiz do projeto:

```powershell
npm install
npm run dev
```

- App: http://localhost:3000

> O frontend lê `VITE_API_URL` (padrão `http://localhost:8000`). Para apontar para
> `127.0.0.1`, rode `cp .env.example .env` e ajuste, ou exporte a variável antes do `npm run dev`.

---

## 3. Logins de demonstração

Senha para todos: **`datacare123`**

| Usuário  | Papel                 | Acessa                                  |
|----------|-----------------------|-----------------------------------------|
| `gestor` | Gestor de UBS         | Dashboard, Visitas, Alertas             |
| `acs1`   | Agente Comunitário    | Nova triagem, Visitas                   |
| `acs2`   | Agente Comunitário    | Nova triagem, Visitas                   |
| `medico` | Profissional de saúde | Nova triagem, Visitas                   |
| `admin`  | Administrador         | Tudo + `/admin`                         |

---

## 4. Testes

```powershell
# Backend (API, modelos, ML) — a partir de backend/
cd backend ; ..\.venv\Scripts\python.exe -m pytest ; cd ..

# Pipeline de dados (ETL + EDA)
$env:PYTHONPATH = "$PWD\data_pipeline"
.\.venv\Scripts\python.exe -m pytest data_pipeline\tests

# Frontend
npm run test:run
```

---

## 5. Alternativa: Docker (tudo em um comando)

Sobe Postgres + Django + React + Redis. Requer Docker Desktop.

```powershell
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

O container do backend roda `migrate` e `seed_demo` automaticamente no boot.
