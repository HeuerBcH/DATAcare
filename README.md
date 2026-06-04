# DATAcare

Repositório da solução **Data Care** (CESAR School — Projeto 6, Grupo 13): saúde digital e ML para APS.

## Estado do repositório

| Área | Status |
|------|--------|
| Frontend (`api/frontend/`) | React + Vite + Tailwind |
| Backend (`api/backend/`) | Django + DRF + JWT |
| Data pipeline (`data_pipeline/`) | Estrutura de pastas pronta |
| Docker | `docker-compose.yaml` configurado |

Estrutura da API: [`api/README.md`](api/README.md).  
Documentação: [`documentacoes/SETUP.md`](documentacoes/SETUP.md), histórias: [`documentacoes/IMPLEMENTACOES.md`](documentacoes/IMPLEMENTACOES.md).

## Pré-requisitos

| Ferramenta | Versão | Na sua máquina |
|------------|--------|----------------|
| Node.js | ≥ 18 | ✅ v22 |
| npm | ≥ 9 | ✅ |
| Python | 3.12 (recomendado para ML) | ✅ 3.12 |
| Git | qualquer | ✅ |
| Docker Desktop | opcional | ✅ |
| PostgreSQL | 15+ (futuro backend) | ❌ não instalado |

## Setup rápido (Windows)

```powershell
cd api\frontend
npm install
cd ..\..

Copy-Item .env.example .env

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r api\backend\requirements.txt
```

### Ambiente virtual Python

```powershell
.\.venv\Scripts\Activate.ps1
```

### Frontend

```powershell
cd api\frontend
npm run dev
```

Abre em **http://localhost:3000**.

### Backend

```powershell
cd api\backend
python manage.py runserver
```

API em **http://localhost:8000/api/v1/**.

Outros scripts: `npm run build`, `npm test`, `npm run lint`, `npm run type-check`.

### Jupyter (EDA / notebooks)

Com o venv ativado:

```powershell
jupyter lab
```

Notebooks em `data_pipeline/notebooks/`.

### ML completo (opcional)

Pacotes extras (MLflow, LightGBM, etc.):

```powershell
pip install -r requirements-ml.txt
```

### SHAP no Windows

`shap` foi deixado comentado em `requirements.txt` porque exige **Microsoft C++ Build Tools**. Para instalar depois:

1. [Build Tools for Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. `pip install "shap>=0.46"`

## Variáveis de ambiente

Arquivo `.env` (criado a partir de `.env.example`):

```
VITE_API_URL=http://localhost:8000
```

`VITE_API_URL` deve apontar para o backend Django (`http://localhost:8000`).

## Estrutura

```
DATAcare/
├── api/
│   ├── backend/         # Django + DRF (templates, static, media)
│   └── frontend/        # React + Vite
├── data_pipeline/       # ETL, ML, notebooks
├── documentacoes/
└── requirements-ml.txt  # ML estendido (opcional)
```
