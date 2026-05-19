# DATAcare

Repositório da solução **Data Care** (CESAR School — Projeto 6, Grupo 13): saúde digital e ML para APS.

## Estado do repositório

| Área | Status |
|------|--------|
| Frontend (React + Vite + Tailwind) | Scaffold na raiz — `npm run dev` |
| Data pipeline (`data_pipeline/`) | Estrutura de pastas pronta |
| Backend (FastAPI) | Ainda não implementado |
| Docker | Arquivos vazios (HU-11) |

Documentação detalhada: [`documentacoes/SETUP.md`](documentacoes/SETUP.md), histórias: [`documentacoes/IMPLEMENTACOES.md`](documentacoes/IMPLEMENTACOES.md).

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
cd c:\Users\rmiranda\Git\Cesar\DATAcare
.\scripts\setup.ps1
```

Ou manualmente:

```powershell
npm install
Copy-Item .env.example .env

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Ambiente virtual Python

```powershell
.\.venv\Scripts\Activate.ps1
```

### Frontend

```powershell
npm run dev
```

Abre em **http://localhost:3000**.

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

Quando o backend existir, aponte essa URL para a API FastAPI.

## Estrutura

```
DATAcare/
├── src/                 # Frontend React
├── data_pipeline/       # ETL, ML, notebooks
├── documentacoes/
├── scripts/setup.ps1
├── package.json
├── requirements.txt     # ML / notebooks (dev)
└── requirements-ml.txt  # ML estendido (opcional)
```
