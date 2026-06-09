# DATAcare

**DATAcare** (CESAR School — Projeto 6, Grupo 13): sistema de inteligência em saúde para UBS em Recife, PE.
Triagem comunitária com ML, dashboard epidemiológico e API REST.

## Estado do repositório

| Área | Branch | Status |
|------|--------|--------|
| Frontend (React + Vite + Tailwind) | `feature/hu09-dashboard` | Dashboard completo |
| Backend Django + JWT/RBAC | `feature/hu03-hu04` | Auth + API REST |
| ETL (limpeza + split) | `feature/data-etl` | Produção |
| EDA (análise exploratória) | `feature/hu04-eda` | Completo |
| ML (2 modelos XGBoost) | `feature/hu05-hu06-ml` | Completo |
| Docker | `main` | Pendente (HU-11) |

## Pré-requisitos

| Ferramenta | Versão |
|------------|--------|
| Node.js | ≥ 18 |
| npm | ≥ 9 |
| Python | 3.10+ |
| PostgreSQL | 15+ (backend) |

## Setup rápido

```bash
# Frontend
npm install
cp .env.example .env
npm run dev          # http://localhost:3000

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r ../requirements.txt
python manage.py migrate
python manage.py runserver
```

## Rodar o dashboard

**Modo demo (sem backend)** — dados mock realistas, sem precisar do Django:

```bash
# Adicione ao .env:
VITE_USE_MOCK=true

npm run dev
# Abra http://localhost:3000
# Login automático como Gestor
```

**Modo real (com backend):**

```bash
# .env sem VITE_USE_MOCK (ou =false)
npm run dev
# Login com usuário criado via: python manage.py createsuperuser
```

## Rodar os modelos ML

```bash
# Ative o virtualenv com as dependências
pip install -r requirements.txt   # ou requirements-ml.txt

# Treinar com dados sintéticos (sem arquivos reais)
PYTHONPATH=data_pipeline python -m src.models.train --model all --synthetic

# Treinar com dados reais (parquets em data_pipeline/data/interim/)
PYTHONPATH=data_pipeline python -m src.models.train --model all

# Rodar testes unitários (usa dados sintéticos, sem parquets)
PYTHONPATH=data_pipeline pytest data_pipeline/tests/ml/ -v
```

### Modelos disponíveis

| Modelo | Classes | Algoritmo |
|--------|---------|-----------|
| `disease_classifier` | dengue / chikungunya / zika / influenza | XGBoost |
| `severity_classifier` | baixo / médio / alto | XGBoost |

## Variáveis de ambiente

```env
# Frontend (Vite)
VITE_API_URL=http://localhost:8000
VITE_USE_MOCK=false          # true para modo demo sem backend

# Backend (Django)
SECRET_KEY=sua-chave-secreta
DEBUG=True
DB_NAME=datacare_db
DB_USER=datacare_user
DB_PASSWORD=datacare_password
DB_HOST=localhost
DB_PORT=5432
```

## Estrutura

```
DATAcare/
├── src/                        # Frontend React
│   ├── pages/                  # Login, Dashboard, Triagem, Predições
│   ├── components/             # KPICard, DiseaseChart, AlertPanel, ...
│   ├── context/AuthContext.tsx
│   └── api/client.ts           # Axios + JWT interceptor
├── backend/                    # Django + DRF
│   ├── apps/users/             # Auth JWT + RBAC
│   ├── apps/patients/
│   ├── apps/predictions/
│   └── config/settings.py
├── data_pipeline/
│   ├── src/
│   │   ├── etl/                # Limpeza e split (feature/data-etl)
│   │   ├── eda/                # Análise exploratória (feature/hu04-eda)
│   │   ├── features/           # Feature engineering (HU-05)
│   │   └── models/             # Treinamento e inferência (HU-06)
│   └── tests/
├── documentacoes/
├── requirements.txt
└── requirements-ml.txt
```

## Scripts úteis

```bash
npm run dev          # Servidor de desenvolvimento frontend
npm run build        # Build de produção
npm run type-check   # Verificar TypeScript sem erros
npm run lint         # ESLint

python manage.py migrate           # Aplicar migrations
python manage.py createsuperuser   # Criar admin
```
