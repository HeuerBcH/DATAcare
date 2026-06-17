# DATAcare — Machine Learning, ETL e MLOps

> **DATAcare** (CESAR School — Projeto 6, Grupo 13): sistema de inteligência em
> saúde para Unidades Básicas de Saúde (UBS) em Recife/PE. Une **triagem
> assistida por Machine Learning**, **dashboard epidemiológico** e **API REST**.

Esta pasta (`documentacoes_ML/`) é a **documentação completa da camada de dados e
de Machine Learning** do projeto: o que construímos, **por que** tomamos cada
decisão, como os dados são tratados, como os modelos são treinados/validados e
como tudo é conteinerizado.

---

## 📚 Mapa da documentação

| Documento | O que cobre |
|-----------|-------------|
| **README.md** (este) | Visão geral do projeto, objetivos, escolhas e estrutura |
| [`EXECUCAO.md`](./EXECUCAO.md) | **Passo a passo para executar tudo** — comandos, pasta `Dados/`, CSVs do Drive |
| [`TRATAMENTO_DE_DADOS.md`](./TRATAMENTO_DE_DADOS.md) | **ETL e tratamento de dados** — limpeza, split, anti-vazamento, features |
| [`VALIDACAO.md`](./VALIDACAO.md) | **Modelagem e validação** — holdout, validação cruzada, busca de hiperparâmetros, resultados |
| [`DOCKER_ML.md`](./DOCKER_ML.md) | **Conteinerização e MLOps** — Docker, MLflow e por que o ETL fica fora do Docker |

> **Quer só rodar?** Vá direto para [`EXECUCAO.md`](./EXECUCAO.md).

---

## 1. O problema e os objetivos

Arboviroses (dengue, chikungunya, zika) e síndromes respiratórias (influenza/SRAG)
sobrecarregam a atenção primária em Recife, especialmente em períodos de surto.
O diagnóstico inicial é difícil porque **as doenças compartilham sintomas** e a
triagem depende de profissionais sobrecarregados.

O DATAcare ataca isso com dois modelos preditivos que apoiam — **não
substituem** — a decisão clínica na UBS:

| Objetivo | Modelo | Saída |
|----------|--------|-------|
| Sugerir a **arbovirose/síndrome** mais provável a partir dos sintomas | `disease_classifier` | dengue · chikungunya · zika · influenza |
| Estimar a **gravidade** do caso para priorizar atendimento | `severity_classifier` | baixo · médio · alto |

Objetivos transversais do projeto de ML:

- **Reprodutibilidade total** — qualquer pessoa reproduz o pipeline do CSV bruto
  ao modelo treinado, com seed fixa e configuração centralizada.
- **Honestidade metodológica** — split temporal anti-vazamento, validação
  cruzada estratificada e métricas adequadas a dados desbalanceados (não só
  acurácia).
- **Rastreabilidade (MLOps)** — todo treino vira um *run* no MLflow, com
  parâmetros, métricas e o modelo versionado.
- **Operabilidade** — o melhor modelo é servido ao backend Django para
  previsões em tempo real, e um dashboard documenta dados e resultados.

---

## 2. Visão geral da arquitetura de dados/ML

```
                        ETL (LOCAL, fora do Docker)
   Dados/*.csv  ──▶  python -m src.etl.run_pipeline  ──▶  data/interim/*.parquet
   (~870 MB)            limpeza + split + anti-leakage          (~69 MB, ~12× menor)
                                                                       │
                          ┌────────────────────────────────────────────┘
                          ▼            TREINO + MLOps (DOCKER)
                  feature engineering ──▶ RF × Árvore ──▶ MLflow (tracking/UI)
                  (src/features)          (validação +        │
                                           busca de hp)       ▼
                                                    models/<task>/ (melhor modelo)
                                                              │
                                                              ▼
                                              backend Django (inferência)  +  dashboard
```

**Decisão central:** o **ETL roda fora do Docker** (gera os parquets localmente);
o **treino, o MLflow, o dashboard e o backend rodam dentro do Docker**. A
justificativa técnica completa está em
[`DOCKER_ML.md`](./DOCKER_ML.md#por-que-o-etl-não-está-no-docker) — em resumo:
os dados brutos são pesados (~870 MB) e o pico de memória do ETL é alto, então
conteinerizá-lo só traria custo (build inflado, risco de OOM) sem benefício,
já que o artefato que importa para a stack é o parquet leve.

---

## 3. Principais decisões de projeto (e o porquê)

| Decisão | Por quê |
|---------|---------|
| **Random Forest + Árvore de Decisão** (sem XGBoost) | Ambos estão na lista permitida pela disciplina. RF é robusto, lida bem com features mistas e desbalanceamento; a Árvore é um *baseline* interpretável para comparação. Comparamos os dois e salvamos o melhor por tarefa. |
| **Split temporal** (não aleatório) | Em produção o modelo só vê casos futuros. Split aleatório vazaria sazonalidade e inflaria as métricas. |
| **Features geográficas** (`uf_code`, `munic_code`) | Surtos são agrupados no espaço-tempo; como os sintomas se sobrepõem, a localização separa as arboviroses. Elevou a acurácia de doença de ~87% para ~93%. |
| **Parquet como formato intermediário** | ~12× menor que CSV, preserva tipos, leitura/escrita rápidas. |
| **MLflow para tracking** | Cada treino é auditável e comparável; o modelo é versionado e servido ao backend. |
| **Configuração centralizada** (`DATASETS`, `config.py`) | Adicionar uma fonte é uma única entrada; sem *magic strings*. |
| **Dados sintéticos como fallback** | Treino e testes rodam em qualquer máquina/CI sem os parquets reais. |
| **ETL fora do Docker** | Dados brutos pesados + pico de RAM do ETL → conteinerizar traria custo sem benefício (ver §2 e `DOCKER_ML.md`). |

---

## 4. Pipeline em quatro etapas

1. **ETL — limpeza** (`src/etl/clean.py`): corrige encoding (latin-1), normaliza
   datas (ISO + DD/MM/AAAA), recodifica `1/2/9 → True/False/NA`, deriva idade do
   `NU_IDADE_N` composto, preserva IDs IBGE e deduplica. → `data/interim/*.parquet`
2. **ETL — split** (`src/etl/split.py`): separa em treino/val/teste com
   estratégia **temporal** e valida **anti-vazamento**. → `data/processed/` + `reports/`
3. **Feature engineering** (`src/features/`): monta as matrizes `(X, y)` de
   doença e severidade (sintomas, comorbidades, demografia, tempo, geografia).
4. **Treino + validação** (`src/models/`): compara RF × Árvore, faz busca de
   hiperparâmetros + validação cruzada, escolhe o melhor e o salva para serving,
   registrando tudo no MLflow.

> Detalhes das etapas 1–3 em [`TRATAMENTO_DE_DADOS.md`](./TRATAMENTO_DE_DADOS.md);
> da etapa 4 em [`VALIDACAO.md`](./VALIDACAO.md).

---

## 5. Modelos e resultados (resumo)

Para cada tarefa treinamos e comparamos **2 algoritmos** e salvamos o melhor (por
CV macro-F1) em `data_pipeline/models/<task>/` (formato `mlflow.sklearn`), que o
backend Django carrega para inferência.

| Tarefa | Modelo selecionado | Acurácia (holdout) |
|--------|--------------------|--------------------|
| Doença | Árvore de Decisão | **~93,6%** |
| Severidade | Random Forest | **~96,3%** |

> Resultados em dados reais (≈400k amostras). A análise completa — incluindo a
> ressalva honesta sobre a macro-F1 baixa da severidade (classes graves
> raríssimas) — está em
> [`VALIDACAO.md`](./VALIDACAO.md#73-resultados-holdout-dados-reais-400k-amostras).

---

## 6. Estrutura de pastas

```
data_pipeline/
├── src/                          # raiz dos pacotes (PYTHONPATH=data_pipeline → imports src.*)
│   ├── etl/                      # ETL: limpeza + split
│   │   ├── config.py             # caminhos + DatasetSpec por fonte (fonte única)
│   │   ├── io_utils.py           # leitura em chunks + escrita parquet
│   │   ├── cleaners/             # base, sinan, srag, pns, taxa_incid
│   │   ├── splitters/            # strategies (temporal/grouped/...) + leakage (validador)
│   │   ├── clean.py              # CLI: limpa N datasets → interim/
│   │   ├── split.py              # CLI: interim/ → processed/{train,val,test}/
│   │   └── run_pipeline.py       # CLI: clean + split numa só chamada
│   ├── features/                 # feature engineering
│   │   ├── config.py             # colunas, labels e mapeamentos (fonte única)
│   │   └── build_features.py     # matrizes (X, y) + geradores sintéticos
│   ├── models/                   # modelos de ML
│   │   ├── config.py             # caminhos de artefato + hiperparâmetros (RF, Árvore)
│   │   ├── pipeline.py           # Pipeline sklearn (imputer → scaler → clf)
│   │   ├── train.py              # CLI: treina e compara, valida e seleciona o melhor
│   │   ├── evaluate.py           # métricas + matriz de confusão + importâncias
│   │   ├── predict.py            # inferência usada pelo backend Django
│   │   └── tracking.py           # configuração do MLflow
│   └── utils/                    # logging compartilhado
├── models/                       # melhor modelo por tarefa (formato MLflow, gitignored)
├── dashboard/                    # Streamlit (ETL & ML)
├── notebooks/                    # EDA pós-split (lê só processed/train/)
├── data/
│   ├── interim/                  # parquet limpo (1 por dataset)
│   ├── processed/{train,val,test}/  # parquet particionado
│   └── reports/{cleaning,leakage,ml}/  # relatórios JSON
└── tests/
    ├── etl/                      # test_cleaners.py, test_splitters.py
    └── ml/                       # test_models.py
```

> Os **dados brutos** (`Dados/*.csv`) ficam **fora do repositório**, na raiz do
> workspace (irmã de `DATAcare/`) — ver [`EXECUCAO.md`](./EXECUCAO.md#2-obter-os-dados-e-criar-a-pasta-dados).

---

## 7. Stack tecnológica

| Camada | Tecnologias |
|--------|-------------|
| ETL & dados | Python 3.11, pandas, pyarrow (parquet) |
| ML | scikit-learn (Random Forest, Decision Tree), imbalanced-learn (SMOTE) |
| MLOps | MLflow 2.10 (tracking + UI + serving) |
| Visualização | Streamlit + Plotly (dashboard ETL/ML) |
| Serving | Django + DRF (carrega o modelo MLflow para inferência) |
| Infra | Docker + Docker Compose, PostgreSQL, Redis |

---

## 8. Comece por aqui

1. **Executar do zero** → [`EXECUCAO.md`](./EXECUCAO.md)
2. **Entender o tratamento de dados** → [`TRATAMENTO_DE_DADOS.md`](./TRATAMENTO_DE_DADOS.md)
3. **Entender a modelagem e validação** → [`VALIDACAO.md`](./VALIDACAO.md)
4. **Entender Docker/MLflow** → [`DOCKER_ML.md`](./DOCKER_ML.md)
