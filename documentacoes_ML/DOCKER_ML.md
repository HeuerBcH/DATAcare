# ML em Docker — Treino + MLflow conteinerizados

Este documento descreve como treinar os modelos e rastrear experimentos do
DATAcare **em containers** (treino + MLflow), atendendo aos requisitos de
*Conteinerização da solução com Docker* e *MLOps (MLflow)* com reprodutibilidade.
O ETL (limpeza + split) roda **fora do Docker** — a justificativa técnica está
na seção [Por que o ETL não está no Docker](#por-que-o-etl-não-está-no-docker).

> Navegação: [README](./README.md) · [Como executar](./EXECUCAO.md) ·
> [Tratamento de dados/ETL](./TRATAMENTO_DE_DADOS.md) · [Validação](./VALIDACAO.md)

## Arquitetura

Três serviços compartilham **uma única imagem** (alvo `ml` do `Dockerfile`
unificado, construído com `target: ml`) — mudando apenas o comando:

| Serviço | Papel | Porta |
|---|---|---|
| `mlflow` | Servidor de tracking + **UI** | http://localhost:5001 |
| `ml-trainer` | Treina/compara os modelos e registra no MLflow | — (one-shot no `up`) |
| `dashboard` | Streamlit (ETL & ML) — a imagem já traz streamlit/plotly | http://localhost:8501 |

> O **ETL (limpeza + split) roda FORA do Docker**. Gere os parquets localmente
> antes de subir a stack (veja [`EXECUCAO.md`](./EXECUCAO.md) e
> [`TRATAMENTO_DE_DADOS.md`](./TRATAMENTO_DE_DADOS.md)).

```
ETL local (fora do Docker)
Dados/*.csv  ──▶  python -m src.etl.run_pipeline  ──▶  data_pipeline/data/interim/*.parquet
                                                              │
                            ┌─────────────────────────────────┘
                            ▼
                       ml-trainer (Docker)  ──▶  models/ + mlflow_data
                            │
                            ▼
                         backend (inferência)
```

- O `ml-trainer` lê os parquets de `data_pipeline/data/interim/` pelo volume
  montado (`.:/app`). Sem eles, o treino cai para **dados sintéticos**.
- O treino e o servidor trocam dados pelo **volume compartilhado** — o servidor
  não precisa estar no ar para o treino funcionar (ele serve apenas a UI).
- O **melhor modelo** de cada tarefa é salvo em `data_pipeline/models/<task>/`
  (formato `mlflow.sklearn`), que o backend Django carrega para inferência.

> Imagem em **Python 3.11** de propósito: o CLI do MLflow 2.10 (`mlflow server`)
> é incompatível com Python 3.12+.

## Por que o ETL não está no Docker

Esta foi uma **decisão de arquitetura deliberada**, não uma omissão. O ETL é a
única etapa que toca os **CSVs brutos** — e são justamente eles que tornam a
conteinerização do ETL cara e sem benefício. A separação segue o princípio de
conteinerizar **o que é servido online** (treino, tracking, API, dashboard) e
manter **fora** o que é um **trabalho batch, offline e pesado** (o ETL).

Os argumentos abaixo se reforçam — juntos, tornam a decisão praticamente
irrefutável.

### 1. Volume dos dados brutos (o fator decisivo)

Os CSVs brutos somam **~870 MB** (`dengue_2025.csv` ~436 MB, `influeza_srag_2025.csv`
~364 MB, `chikungunya_2025.csv` ~67 MB, `zika_2025.csv` ~4 MB). Conteinerizar o
ETL significaria **levar esses ~870 MB para dentro do Docker** de um de dois
jeitos, ambos ruins:

- **Copiá-los na imagem** (`COPY`): infla o *build context* e a imagem em quase
  1 GB, deixa o build lento, estoura cache de camadas a cada mudança nos dados e
  versiona dado pesado dentro de um artefato que deveria ser enxuto.
- **Montá-los por volume**: cria um acoplamento frágil entre o host e o
  container só para uma tarefa que roda raramente — sem ganho real de
  portabilidade, já que os brutos precisam existir no host de qualquer forma.

E o ponto-chave: **o resultado do ETL é leve**. Os ~870 MB de CSV viram **~69 MB
de parquet** (redução de **~12×**). É o parquet — não o CSV — que a stack
conteinerizada consome. Mover ~870 MB de brutos para dentro do Docker, a cada
build/subida, para produzir 69 MB que poderiam ser gerados uma vez fora dele, é
puro desperdício de I/O, disco e tempo.

### 2. Pico de memória do ETL → risco de OOM (exit 137)

A limpeza lê CSVs gigantes e **concatena DataFrames em memória** (mesmo lendo em
chunks, o passe global de deduplicação materializa o dataset). Isso gera um
**pico de RAM alto e pouco previsível**. O treino conteinerizado já vive no
limite de memória padrão do Docker (8 GB) — tanto que precisamos limitar
`ML_N_JOBS` para evitar **OOM (exit 137)**, como documentado abaixo. Colocar o
ETL no mesmo ambiente conteinerizado adicionaria **outro consumidor pesado de
memória**, aumentando a probabilidade de o kernel matar processos. Rodando o ETL
no host, ele usa a RAM da máquina livremente, sem disputar com os serviços da
stack.

### 3. Natureza do ETL: batch, offline e raro

O ETL **não é um serviço** — não responde requisições, não precisa estar "no
ar". É um **job batch** que roda **apenas quando os dados brutos mudam** (algo
raro). Containers brilham para processos **de longa duração ou servidos**
(MLflow, API, dashboard); para um script offline executado esporadicamente pelo
time de dados, o overhead de empacotar, transportar e orquestrar não se paga.

### 4. Dados brutos já vivem fora do versionamento

Os ~870 MB de CSV são públicos, porém pesados, e ficam **fora do repositório**
(gitignored), distribuídos via Drive. Forçá-los para dentro do contexto de build
do Docker contrariaria essa decisão e exigiria que **toda máquina** tivesse os
brutos disponíveis no momento do build — quebrando a portabilidade que o Docker
deveria garantir.

### 5. Separação de responsabilidades (boas práticas de MLOps)

A fronteira fica limpa e fácil de raciocinar:

| Etapa | Onde roda | Por quê |
|-------|-----------|---------|
| **ETL** (limpeza + split) | **Host** (local) | Batch, offline, pesado em dados/RAM; gera parquet leve |
| **Treino + MLflow + dashboard + backend** | **Docker** | Serviços/processos reproduzíveis e servíveis, consomem o parquet leve |

> **Em uma frase:** conteinerizar o ETL custaria ~870 MB de dado pesado dentro
> do Docker e um risco real de OOM, para produzir um parquet de ~69 MB que é
> trivialmente gerado fora dele — então o ETL roda no host e entrega à stack
> conteinerizada exatamente o artefato leve de que ela precisa.

## Comandos

Todos a partir da pasta `DATAcare/` (onde está o `docker-compose.yaml`).

### 0. Rodar o ETL (fora do Docker, antes de subir a stack)

O ETL **não está mais no Docker**. Gere os parquets limpos localmente:

```powershell
# Na raiz do projeto (DATAcare/), com o virtualenv ativo:
$env:PYTHONPATH = "$PWD\data_pipeline"
python -m src.etl.run_pipeline                 # todos os datasets
python -m src.etl.run_pipeline --sample 5000   # dry-run rápido
```

Os CSVs brutos devem estar em `../Dados/` (irmão de `DATAcare/`) ou no caminho
definido por `DATACARE_RAW_DIR`. Detalhes completos em [`EXECUCAO.md`](./EXECUCAO.md).
Os parquets vão para `data_pipeline/data/interim/`, que o `ml-trainer` lê pelo
volume montado. Sem eles, o treino usa **dados sintéticos**.

### 1. Subir a stack completa (treino automático)

```bash
docker compose up -d
# Ordem: mlflow (healthy) + ml-trainer (treina) -> backend -> frontend
# UI MLflow: http://localhost:5001
# Dashboard ML/ETL (Streamlit): http://localhost:8501
```

O serviço `ml-trainer` roda **automaticamente** na subida. Ele é
one-shot (`restart: "no"`) e o **backend só sobe depois** que o treino termina
com sucesso.

**Controle do treino** (opcional, no `.env`):

| Variável | Default | Efeito |
|---|---|---|
| `FORCE_ML_TRAIN` | `false` | `true` = sempre treina de novo |
| `SKIP_ML_TRAIN` | `false` | `true` = pula o treino (sobe mais rápido) |
| `ML_MAX_ROWS` | `120000` | cap de linhas do treino; `0` = todas |
| `ML_N_JOBS` | `2` | paralelismo da busca de hiperparâmetros (veja abaixo) |

Se os modelos já existem em `data_pipeline/models/*/MLmodel`, o treino é **pulado**
na subida seguinte (a menos que `FORCE_ML_TRAIN=true`).

> **Memória / OOM (exit 137).** A busca de hiperparâmetros (`RandomizedSearchCV`)
> roda em paralelo e **cada worker duplica os dados de treino em memória**. Com
> `n_jobs=-1` (um por core) isso multiplicava o pico de RAM e estourava o limite
> do Docker (8GB) — o container do treino era morto pelo kernel (**exit 137**).
> Agora o paralelismo é limitado por `ML_N_JOBS` (default **2**) e a memória é
> liberada entre as tarefas (disease → severity). Se o treino ainda cair por
> falta de memória, reduza `ML_N_JOBS=1` e/ou `ML_MAX_ROWS`; com mais RAM,
> aumente `ML_N_JOBS` para acelerar a busca.

### 2. Subir só o MLflow (UI)

```bash
docker compose up -d mlflow
# UI em http://localhost:5001
```

### 3. Rodar só o ETL (fora do Docker)

O ETL roda localmente — veja a seção 0 acima e o [`EXECUCAO.md`](./EXECUCAO.md):

```powershell
$env:PYTHONPATH = "$PWD\data_pipeline"
python -m src.etl.run_pipeline
```

### 4. Treinar manualmente (opcional)

```bash
docker compose run --rm ml-trainer

# Variações:
docker compose run --rm ml-trainer python -m src.models.train --model all --search grid
docker compose run --rm ml-trainer python -m src.models.train --model all --synthetic
docker compose run --rm ml-trainer python -m src.models.train --model disease --max-rows 0
```

### 5. Ver os resultados

Abra http://localhost:5001 e compare os runs nos experimentos
`datacare-disease-classification` e `datacare-severity-classification`
(parâmetros, métricas e modelos de cada algoritmo).

## Dados

- Com os **parquets reais** em `data_pipeline/data/interim/` (gerados pelo ETL),
  o treino usa dados reais e atinge **disease ≈ 76,4%** (predição dirigida por
  sintomas) e **severity ≈ 99,4%**.
- Sem os parquets, o treino cai automaticamente para **dados sintéticos**
  (útil para reproduzir em qualquer máquina / CI).

O backend lê os modelos de `data_pipeline/models/` (volume compartilhado) e
passa a servir previsões reais após o `ml-trainer` concluir.

## Arquivos relevantes

| Arquivo | Função |
|---|---|
| `Dockerfile` (alvo `ml`) | Imagem de ML — serve treino, servidor MLflow e dashboard Streamlit |
| `docker-compose.yaml` | Serviços `mlflow` e `ml-trainer` |
| `scripts/docker-train.sh` | Entrypoint do treino no compose |
| `.dockerignore` | Mantém dados/`mlruns`/venv fora do contexto de build |
| `data_pipeline/src/etl/run_pipeline.py` | ETL (limpeza + split) — roda fora do Docker |
| `data_pipeline/src/models/train.py` | Treino/comparação dos modelos |
| `data_pipeline/src/models/tracking.py` | Config do MLflow (`MLFLOW_TRACKING_URI`) |
