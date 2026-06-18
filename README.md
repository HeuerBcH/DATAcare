# DATAcare

**DATAcare** (CESAR School — Projeto 6, Grupo 13): sistema de inteligência em saúde para UBS em Recife, PE.
Triagem comunitária com ML, dashboard epidemiológico e API REST.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | React + Vite + Tailwind CSS |
| Backend | Django 4.2 + DRF + JWT |
| ML Pipeline | scikit-learn (Random Forest — padrão; Árvore de Decisão como comparação) |
| Tracking | MLflow 2.10 |
| Dashboard ML | Streamlit |
| Banco de dados | PostgreSQL 15 |
| Infraestrutura | Docker Compose |

## Subir tudo com Docker (recomendado)

```bash
cp .env.example .env   # ajuste as variáveis se necessário
docker compose up -d
```

O compose sobe, em ordem, mlflow → ml-trainer → backend → frontend + dashboard.
Ao final, os usuários de demonstração e as triagens de teste já estão criados automaticamente.

| Serviço | URL |
|---------|-----|
| Frontend (React) | http://localhost:3000 |
| Backend (API Django) | http://localhost:8000 |
| Dashboard ML (Streamlit) | http://localhost:8501 |
| MLflow UI | http://localhost:5001 |

### Logins de demonstração

Senha para todos: **`datacare123`**

| Usuário | Papel |
|---------|-------|
| `gestor` | Gestor de UBS |
| `acs1` | Agente Comunitário |
| `acs2` | Agente Comunitário |
| `medico` | Profissional de Saúde |
| `admin` | Administrador |

## Rodar localmente (sem Docker)

Consulte [`documentacoes/RODAR_LOCAL.md`](documentacoes/RODAR_LOCAL.md) para o passo a passo completo.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt
python manage.py migrate
python manage.py seed_demo        # cria usuários e triagens de demo
python manage.py runserver

# Frontend (outro terminal)
cd frontend
npm install
npm run dev    # http://localhost:3000
```

> **Modo demo (sem backend):** defina `VITE_USE_MOCK=true` no `.env` para o frontend
> usar dados mock realistas (Dashboard e Pacientes), dispensando o Django.

## Pipeline de ML

Consulte [`documentacoes_ML/EXECUCAO.md`](documentacoes_ML/EXECUCAO.md) para o guia completo de ETL + treino.

```bash
# Treinar localmente (após rodar o ETL)
export PYTHONPATH=data_pipeline
python -m src.models.train --model all

# Testes do pipeline (dados sintéticos, sem precisar dos CSVs)
python -m pytest data_pipeline/tests -v
```

### Modelos

| Modelo | Classes | Algoritmo |
|--------|---------|-----------|
| `disease_classifier` | dengue / chikungunya / zika / influenza | Random Forest |
| `severity_classifier` | baixo / médio / alto | Random Forest |

## Estrutura

```
DATAcare/
├── frontend/                   # React + Vite
│   └── src/
│       ├── pages/              # Login, Dashboard, TriageForm, Visits
│       ├── components/         # KPICard, DiseaseChart, AlertPanel, ...
│       ├── context/            # AuthContext (JWT)
│       └── api/                # client.ts (Axios), mock.ts
├── backend/                    # Django + DRF
│   └── apps/
│       ├── users/              # Auth JWT + RBAC + seed_demo
│       ├── patients/           # Visit (triagem) + Patient
│       └── api/                # Endpoints ML, dashboard, predict
├── data_pipeline/              # Pipeline de ML (PYTHONPATH=data_pipeline)
│   ├── src/
│   │   ├── etl/                # Limpeza e split dos CSVs SINAN
│   │   ├── features/           # Feature engineering
│   │   ├── models/             # Treino, avaliação e inferência
│   │   └── utils/
│   ├── dashboard/              # Streamlit (ETL + métricas ML)
│   ├── models/                 # Artefatos treinados (MLflow)
│   ├── data/                   # interim/ · processed/ · reports/
│   └── tests/                  # tests/etl · tests/ml
├── documentacoes/              # Setup, rodar local, implementações
├── documentacoes_ML/           # ETL, treino, validação, Docker ML
├── docker-compose.yaml
├── Dockerfile                  # multi-stage: backend (Python 3.12) + ml (Python 3.11)
├── Dockerfile.frontend
└── requirements.txt
```

## Scripts úteis

```bash
# Recriar dados de demonstração
docker exec datacare-backend python manage.py seed_demo --reset

# Ver logs do treino ML
docker logs datacare-mlflow

# Rodar testes do pipeline
export PYTHONPATH=data_pipeline
python -m pytest data_pipeline/tests -v
```
