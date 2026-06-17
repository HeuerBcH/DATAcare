# Como Executar o Pipeline de ML do DATAcare — Guia Completo

Este documento é o **passo a passo definitivo** para sair do zero (repositório
recém-clonado) até ter os **modelos treinados, rastreados no MLflow e servindo
previsões**. Ele cobre desde a obtenção dos dados brutos até o `docker compose up`.

Leia na ordem. Cada etapa traz os comandos exatos para **Windows (PowerShell)** e,
quando útil, o equivalente em **Linux/macOS (bash)**.

> Visão arquitetural em uma frase: **o ETL roda fora do Docker** (gera os
> `parquet` limpos localmente) e **o treino + tracking + dashboard rodam dentro
> do Docker**. O porquê dessa divisão está detalhado em
> [`DOCKER_ML.md`](./DOCKER_ML.md#por-que-o-etl-não-está-no-docker).

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Obter os dados e criar a pasta `Dados/`](#2-obter-os-dados-e-criar-a-pasta-dados)
3. [Preparar o ambiente Python](#3-preparar-o-ambiente-python-para-o-etl)
4. [Rodar o ETL (limpeza + split)](#4-rodar-o-etl-limpeza--split)
5. [Treinar os modelos](#5-treinar-os-modelos)
6. [Subir a stack completa com Docker](#6-subir-a-stack-completa-com-docker)
7. [Conferir os resultados](#7-conferir-os-resultados)
8. [Rodar os testes](#8-rodar-os-testes)
9. [Fluxo resumido (TL;DR)](#9-fluxo-resumido-tldr)
10. [Solução de problemas](#10-solução-de-problemas)

---

## 1. Pré-requisitos

| Ferramenta | Versão | Para quê |
|------------|--------|----------|
| Python | **3.11** (recomendado) ou 3.10+ | Rodar o ETL e o treino localmente |
| pip + venv | — | Isolar as dependências |
| Docker + Docker Compose | recente | Subir treino, MLflow, dashboard e backend |
| Git | — | Clonar o repositório |
| RAM | **≥ 8 GB** | O ETL lê CSVs grandes (dengue ~436 MB, SRAG ~364 MB) |
| Disco livre | **≥ 3 GB** | Dados brutos (~870 MB) + parquets + artefatos |

> **Por que Python 3.11?** O servidor do MLflow 2.10 usado no projeto é
> incompatível com Python 3.12+. Para rodar tudo de forma idêntica ao Docker,
> use 3.11 no ambiente local. Para *só* o ETL, qualquer 3.10+ serve.

---

## 2. Obter os dados e criar a pasta `Dados/`

Os arquivos CSV brutos do SUS **não fazem parte do repositório** (somam ~870 MB e
são públicos, porém pesados — ficam fora do controle de versão). Eles foram
**disponibilizados pela nossa equipe em um Google Drive**.

### 2.1. Baixe os CSVs do Drive

> 📁 **Os CSVs necessários estão no Drive fornecido pela equipe.**
> Baixe os **4 arquivos** abaixo (são exatamente os que o pipeline consome):

| Arquivo (nome exato) | Fonte | Tamanho aprox. |
|----------------------|-------|----------------|
| `dengue_2025.csv` | SINAN — Dengue | ~436 MB |
| `chikungunya_2025.csv` | SINAN — Chikungunya | ~67 MB |
| `zika_2025.csv` | SINAN — Zika | ~4 MB |
| `influeza_srag_2025.csv` | SIVEP-Gripe — SRAG/Influenza | ~364 MB |

> ⚠️ **Mantenha os nomes dos arquivos exatamente como estão na tabela.** O
> pipeline procura por esses nomes (definidos em
> `data_pipeline/src/etl/config.py`). Renomear quebra a descoberta automática.

### 2.2. Onde colocar a pasta `Dados/`

Crie uma pasta chamada **`Dados`** na **raiz do workspace**, ou seja,
**ao lado da pasta `DATAcare/`** (são irmãs — a `Dados/` **NÃO** fica dentro de
`DATAcare/`). A estrutura final precisa ficar assim:

```
<raiz do workspace>/
├── DATAcare/            <- o repositório do projeto
│   ├── data_pipeline/
│   ├── backend/
│   ├── frontend/
│   └── ...
└── Dados/               <- VOCÊ CRIA ESTA PASTA (irmã de DATAcare/)
    ├── dengue_2025.csv
    ├── chikungunya_2025.csv
    ├── zika_2025.csv
    └── influeza_srag_2025.csv
```

Criar a pasta e conferir (a partir de dentro de `DATAcare/`):

```powershell
# PowerShell (Windows) — cria ../Dados (irmã de DATAcare)
New-Item -ItemType Directory -Force -Path ..\Dados
# ... copie/mova os 4 CSVs baixados do Drive para ..\Dados ...
Get-ChildItem ..\Dados        # deve listar os 4 CSVs
```

```bash
# bash (Linux/macOS)
mkdir -p ../Dados
# ... mova os 4 CSVs para ../Dados ...
ls -lh ../Dados
```

### 2.3. (Opcional) Usar outro caminho para os dados

Se você preferir guardar os CSVs em outro lugar (ex.: outro disco), aponte a
variável de ambiente `DATACARE_RAW_DIR` para a pasta onde eles estão:

```powershell
$env:DATACARE_RAW_DIR = "D:\meus_dados\datacare"
```

```bash
export DATACARE_RAW_DIR="/mnt/dados/datacare"
```

Sem essa variável, o pipeline assume automaticamente `../Dados` (irmã de
`DATAcare/`).

---

## 3. Preparar o ambiente Python (para o ETL)

O ETL roda **localmente** (fora do Docker). Crie um ambiente virtual e instale
as dependências.

A partir da pasta `DATAcare/`:

```powershell
# PowerShell (Windows)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```bash
# bash (Linux/macOS)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Os pacotes de ML são importados pelo prefixo `src.` — para isso o Python precisa
enxergar a pasta `data_pipeline` como raiz de pacotes. Defina o `PYTHONPATH`
**na mesma sessão de terminal** em que for rodar os comandos:

```powershell
# PowerShell (Windows) — a partir de DATAcare/
$env:PYTHONPATH = "$PWD\data_pipeline"
```

```bash
# bash (Linux/macOS) — a partir de DATAcare/
export PYTHONPATH=data_pipeline
```

> Se você abrir um terminal novo, refaça `Activate` e `PYTHONPATH`.

---

## 4. Rodar o ETL (limpeza + split)

O ETL faz duas coisas: **limpa** os CSVs brutos (corrige encoding, datas,
códigos, deduplica) e **separa** cada dataset em treino/validação/teste com
checagem anti-vazamento. A explicação completa do que acontece em cada etapa
está em [`TRATAMENTO_DE_DADOS.md`](./TRATAMENTO_DE_DADOS.md).

Todos os comandos a partir de `DATAcare/`, com o venv ativo e o `PYTHONPATH`
definido (etapa 3).

### 4.1. Teste rápido primeiro (dry-run, ~1 min)

Antes de processar tudo, valide que os caminhos e os CSVs estão certos rodando
em **5 mil linhas por dataset**:

```powershell
python -m src.etl.run_pipeline --sample 5000
```

Se isso terminar sem erro, os caminhos estão corretos.

### 4.2. Pipeline completo (todos os datasets)

```powershell
python -m src.etl.run_pipeline
```

Saídas geradas:

| Saída | Onde |
|-------|------|
| Parquet limpo (1 por dataset) | `data_pipeline/data/interim/*.parquet` |
| Partições treino/val/teste | `data_pipeline/data/processed/{train,val,test}/` |
| Relatórios de limpeza | `data_pipeline/data/reports/cleaning/*.json` |
| Relatórios de vazamento (leakage) | `data_pipeline/data/reports/leakage/*.json` |

### 4.3. Variações úteis

```powershell
# Só um dataset
python -m src.etl.run_pipeline --dataset sinan_dengue

# Etapas isoladas (limpeza e split separados)
python -m src.etl.clean --dataset sinan_dengue --sample 5000
python -m src.etl.split --dataset sinan_dengue --train 0.7 --val 0.15 --test 0.15
```

> ✅ **O que importa para as próximas etapas** são os arquivos em
> `data_pipeline/data/interim/*.parquet` — é deles que o treino lê as features.

---

## 5. Treinar os modelos

O treino compara **Random Forest** e **Árvore de Decisão** em duas tarefas
(doença e severidade), faz busca de hiperparâmetros + validação cruzada, escolhe
o melhor por cada tarefa e o salva para serving. Detalhes da estratégia de
validação em [`VALIDACAO.md`](./VALIDACAO.md).

Você pode treinar de duas formas: **localmente** ou **via Docker** (etapa 6).

### 5.1. Treino local

```powershell
# Dados reais (lê os parquets gerados pelo ETL na etapa 4)
python -m src.models.train --model all

# Dados sintéticos (não precisa dos parquets — útil para testar a máquina/CI)
python -m src.models.train --model all --synthetic
```

Saídas:

| Saída | Onde |
|-------|------|
| Melhor modelo por tarefa (formato MLflow) | `data_pipeline/models/<task>/` |
| Relatórios de métricas | `data_pipeline/data/reports/ml/*_report.json` |
| Runs de experimento | `data_pipeline/mlruns/` |

> Se os parquets reais não existirem, o treino **cai automaticamente para dados
> sintéticos** — ele nunca quebra por falta de dados.

### 5.2. Variações úteis

```powershell
python -m src.models.train --model all --search grid        # Grid Search
python -m src.models.train --model all --search random --n-iter 30
python -m src.models.train --model all --search none         # hiperparâmetros fixos
python -m src.models.train --model disease --max-rows 0      # usar todas as linhas
```

---

## 6. Subir a stack completa com Docker

Com os parquets já gerados (etapa 4), suba treino + MLflow + dashboard + backend
+ frontend de uma vez. **Todos os comandos a partir de `DATAcare/`** (onde está
o `docker-compose.yaml`).

```bash
docker compose up -d
```

Ordem de subida orquestrada pelo compose:

```
mlflow (fica healthy) ─▶ ml-trainer (treina, one-shot) ─▶ backend ─▶ frontend
                                       └─▶ dashboard
```

URLs depois que tudo sobe:

| Serviço | URL |
|---------|-----|
| Backend (API Django) | http://localhost:8000 |
| Frontend (React/Vite) | http://localhost:3000 |
| Dashboard ETL/ML (Streamlit) | http://localhost:8501 |
| MLflow UI (experimentos) | http://localhost:5000 |

> O `ml-trainer` lê os parquets de `data_pipeline/data/interim/` pelo volume
> montado. **Sem os parquets, ele treina com dados sintéticos** (a stack sobe
> do mesmo jeito). Para previsões reais, rode o ETL (etapa 4) **antes** do `up`.

Controle do treino pelo `.env` (na raiz `DATAcare/`):

| Variável | Default | Efeito |
|----------|---------|--------|
| `FORCE_ML_TRAIN` | `false` | `true` = sempre retreina no `up` |
| `SKIP_ML_TRAIN` | `false` | `true` = pula o treino (sobe mais rápido) |
| `ML_MAX_ROWS` | `120000` | cap de linhas no treino; `0` = todas |
| `ML_N_JOBS` | `2` | paralelismo da busca (baixo evita OOM) |

Subir apenas serviços específicos:

```bash
docker compose up -d mlflow        # só a UI do MLflow (porta 5000)
docker compose up -d dashboard     # só o dashboard (porta 8501)
docker compose run --rm ml-trainer # treinar manualmente, uma vez
```

Detalhes completos da conteinerização em [`DOCKER_ML.md`](./DOCKER_ML.md).

---

## 7. Conferir os resultados

1. **MLflow UI** — http://localhost:5000 : compare os runs dos experimentos
   `datacare-disease-classification` e `datacare-severity-classification`
   (parâmetros, métricas, modelos de cada algoritmo).
2. **Dashboard Streamlit** — http://localhost:8501 : visão de ETL (linhas,
   duplicatas, split, vazamento) e de ML (matriz de confusão, métricas por
   classe, importância de features, comparação RF × Árvore).
3. **Relatórios JSON** — em `data_pipeline/data/reports/` (limpeza, leakage, ml).

---

## 8. Rodar os testes

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest data_pipeline/tests/etl    # ETL: cleaners + splitters
python -m pytest data_pipeline/tests/ml     # ML: pipelines + métricas (dados sintéticos)
python -m pytest data_pipeline/tests        # tudo
```

> `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` contorna uma instalação quebrada de
> Hydra/omegaconf no Python global. Em venv isolado costuma ser dispensável.

---

## 9. Fluxo resumido (TL;DR)

```powershell
# 0. Baixe os 4 CSVs do Drive e coloque-os em ../Dados (irmã de DATAcare/)

# 1. Ambiente (a partir de DATAcare/)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "$PWD\data_pipeline"

# 2. ETL local (gera os parquets)
python -m src.etl.run_pipeline --sample 5000   # valida rápido
python -m src.etl.run_pipeline                 # processa tudo

# 3. Stack completa (treina + MLflow + dashboard + backend + frontend)
docker compose up -d

# 4. Resultados: http://localhost:5000 (MLflow) e http://localhost:8501 (dashboard)
```

---

## 10. Solução de problemas

| Sintoma | Causa provável | Solução |
|---------|----------------|---------|
| `Arquivo bruto não encontrado: .../Dados/dengue_2025.csv` | Pasta `Dados/` no lugar errado ou CSV renomeado | Confirme que `Dados/` é **irmã** de `DATAcare/` e que os nomes batem com a tabela da [etapa 2.1](#21-baixe-os-csvs-do-drive) |
| `ModuleNotFoundError: src` | `PYTHONPATH` não definido | Rode `$env:PYTHONPATH = "$PWD\data_pipeline"` a partir de `DATAcare/` |
| Treino usa "dados sintéticos" sem querer | Parquets ausentes em `data/interim/` | Rode o ETL (etapa 4) antes do treino |
| Container do treino morto com **exit 137** | OOM (memória estourada) | Reduza `ML_N_JOBS=1` e/ou `ML_MAX_ROWS` no `.env` |
| `mlflow server` falha no Python local | Python 3.12+ | Use Python 3.11 ou rode o MLflow só via Docker |
| ETL muito lento / trava | CSV gigante (dengue/SRAG) | Teste antes com `--sample 5000`; garanta ≥ 8 GB de RAM |
```