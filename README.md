# DATAcare

Repositório destinado à criação de solução para disciplina de Projeto 6 (CESAR School) - Grupo 13

**Data Care** é uma camada inteligente de apoio à decisão para a **Atenção Primária à Saúde (APS)**
no SUS. Transforma os dados coletados pelo **Agente Comunitário de Saúde (ACS)** em visitas
domiciliares em **priorização de risco por Machine Learning**, **dashboards** para o gestor da UBS
e **alertas inteligentes** — sem substituir o julgamento clínico.

> Briefing completo em [`documentacoes/PROMPT.md`](documentacoes/PROMPT.md) ·
> Histórias de usuário em [`documentacoes/IMPLEMENTACOES.md`](documentacoes/IMPLEMENTACOES.md) ·
> **Como rodar:** [`documentacoes/RODAR_LOCAL.md`](documentacoes/RODAR_LOCAL.md)

---

## ✨ O que o MVP entrega

- **Formulário de triagem do ACS** (HU-01): coleta guiada de dados pessoais, sintomas (com
  severidade e duração), comorbidades e medicações, com validação e rascunho automático.
- **Classificação de risco por ML** (HU-06): modelo que classifica cada triagem em
  **BAIXO / MÉDIO / ALTO**, integrado à API e executado a cada visita.
- **Dashboard do gestor** (HU-09): KPIs, distribuição de risco, evolução temporal, sintomas
  mais comuns e lista de pacientes críticos — storytelling de dados acionável.
- **Alertas inteligentes** (HU-10): regras automáticas (alto risco, sinais respiratórios,
  acompanhamento em atraso) com deduplicação.
- **Autenticação JWT com papéis** (HU-03): gestor, ACS, profissional de saúde e admin, cada um
  com sua interface.
- **Pipeline de dados** (HU-04/05): feature engineering, geração de dados sintéticos coerentes e
  EDA com relatórios e gráficos.

## 🏗️ Arquitetura

```
DATAcare/
├── backend/                 # Django + DRF (API REST, JWT, admin)
│   ├── apps/
│   │   ├── users/           # autenticação e papéis (RBAC)
│   │   ├── triage/          # ⭐ domínio ACS: Patient, Visit, Symptom, Comorbidity, Alert
│   │   ├── patients/        # modelo clínico (mantido do scaffold)
│   │   └── predictions/     # registro de modelos/predições
│   └── tests/               # testes de API, modelos e integração ML
├── data_pipeline/           # ETL + ML + EDA
│   └── src/
│       ├── etl/             # limpeza e split dos dados públicos do SUS (SINAN/SRAG/PNS)
│       ├── ml/              # ⭐ features, dados sintéticos, treino e inferência do modelo
│       └── eda/             # análise exploratória
├── src/                     # ⭐ Frontend React + Vite + TypeScript + Tailwind
│   ├── pages/               # Login, Dashboard, TriageForm, Visits, Alerts
│   ├── components/          # Layout, RiskBadge, StatCard…
│   └── lib/                 # cliente axios + JWT, tipos
└── docker-compose.yaml      # Postgres + Django + React + Redis
```

**Stack:** Django 4.2 · Django REST Framework · SimpleJWT · scikit-learn · pandas ·
React 18 · Vite · TypeScript · Tailwind · Recharts · PostgreSQL (Docker) / SQLite (local).

## 🚀 Início rápido (local, sem Docker)

```powershell
# Backend
py -3.10 -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "$PWD\data_pipeline" ; python -m src.ml.train
cd backend ; python manage.py migrate ; python manage.py seed_demo --reset ; cd ..
python backend\manage.py runserver

# Frontend (outro terminal)
npm install ; npm run dev
```

Acesse http://localhost:3000 e entre com **`gestor`** ou **`acs1`** (senha `datacare123`).
Passo a passo detalhado em [`documentacoes/RODAR_LOCAL.md`](documentacoes/RODAR_LOCAL.md).

## 🧪 Testes

```powershell
cd backend ; ..\.venv\Scripts\python.exe -m pytest ; cd ..      # backend (API/ML)
$env:PYTHONPATH = "$PWD\data_pipeline"
.\.venv\Scripts\python.exe -m pytest data_pipeline\tests        # pipeline (ETL/EDA)
npm run test:run                                                # frontend
```

## 📝 Notas

- **Dados sintéticos:** os ~2 GB de dados reais do SUS não acompanham o repositório, e os
  microdados epidemiológicos (SINAN/SRAG/PNS) são populacionais. Para o MVP, o modelo é treinado
  com **triagens sintéticas coerentes** geradas por regra clínica + ruído
  ([`data_pipeline/src/ml/synthetic.py`](data_pipeline/src/ml/synthetic.py)). A interface de
  features é a mesma — basta trocar a fonte por dados reais de ACS no futuro.
- **Apoio à decisão:** o modelo **não** toma decisões; apenas prioriza para o profissional.
