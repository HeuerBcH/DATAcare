# Estratégia de Validação e Busca de Hiperparâmetros

Este documento descreve **como** a solução de Machine Learning do DATAcare é
validada e **por que** cada estratégia foi escolhida. Cobre o requisito de
*Validação* do projeto: Holdout, Validação Cruzada, Leave-One-Out (quando
aplicável) e Random/Grid Search, com a devida justificativa.

> Código de referência: `data_pipeline/src/models/train.py` e
> `data_pipeline/src/models/config.py`.
>
> Navegação: [README](./README.md) · [Como executar](./EXECUCAO.md) ·
> [Tratamento de dados/ETL](./TRATAMENTO_DE_DADOS.md) · [Docker/MLflow](./DOCKER_ML.md)

---

## 1. Visão geral

Treinamos dois classificadores multiclasse sobre dados reais do SINAN/SRAG.
Para **cada** classificador comparamos **dois algoritmos da lista permitida**
— **Random Forest** e **Árvore de Decisão** (XGBoost foi removido do projeto) —
e o melhor (por validação cruzada) é salvo para serving.

| Modelo | Tarefa | Classes |
|---|---|---|
| `disease_classifier` | Tipo de arbovirose/síndrome | dengue, chikungunya, zika, influenza |
| `severity_classifier` | Gravidade do caso | baixo, médio, alto |

O fluxo de validação de cada modelo é:

```
dados → split Holdout (treino/teste) → para cada algoritmo:
          [Busca de hiperparâmetros] → Validação Cruzada (K-Fold) no treino
          → re-treino final → avaliação no teste (holdout) → log no MLflow
      → seleção do melhor algoritmo → salvamento p/ serving
```

> Resultados em dados reais (≈400k amostras, ver §7): **disease 93,6%** e
> **severity 96,3%** de acurácia no holdout.

---

## 2. Estratégias de validação

### 2.1. Holdout (treino/teste)

- **Implementação:** `train_test_split(test_size=0.2, stratify=y, random_state=42)`.
- O conjunto de **teste (20%)** fica completamente separado e só é usado na
  avaliação final — nunca na busca nem na validação cruzada. Isso dá uma
  estimativa honesta da generalização.
- **Estratificado** (`stratify=y`): preserva a proporção das classes em treino e
  teste, essencial porque as classes são **desbalanceadas** (ex.: gravidade
  "alto" é rara).

**Justificativa:** o Holdout é a forma padrão de obter uma métrica final em um
conjunto que o modelo nunca viu. Com centenas de milhares de amostras, 20% já
formam um conjunto de teste grande e estatisticamente representativo.

### 2.2. Validação Cruzada (K-Fold estratificado)

- **Implementação:** `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`
  com `cross_val_score(scoring="f1_macro")`, aplicada **dentro do conjunto de
  treino**.
- Reporta `cv_f1_mean` e `cv_f1_std` (média e desvio-padrão da macro-F1 nos 5
  folds), registrados no MLflow.

**Justificativa:**
- **Estratificado** porque as classes são desbalanceadas — o K-Fold simples
  poderia gerar folds sem nenhuma amostra das classes raras.
- **5 folds** é o melhor custo/benefício: estimativa estável da variância do
  modelo sem o custo de muitos re-treinos.
- A métrica é **macro-F1**, que pondera todas as classes igualmente (não deixa a
  classe majoritária dominar a avaliação) — adequada para dados desbalanceados.

### 2.3. Leave-One-Out (LOO) — *não aplicável*

- **Status:** não utilizado, **por inviabilidade computacional**.
- O LOO treina o modelo *N* vezes (uma por amostra). Com bases de **centenas de
  milhares a milhões** de registros (ex.: ~1,6 milhão de notificações de
  dengue), isso significaria milhões de treinos de Random Forest/Árvore de
  Decisão — completamente impraticável.
- O LOO faz sentido em **bases pequenas** (dezenas/poucas centenas de amostras),
  onde não se pode "abrir mão" de dados para um fold de teste. **Não é o nosso
  caso.**

**Justificativa da decisão:** o K-Fold estratificado (5 folds) fornece a mesma
informação que o LOO buscaria (estimativa robusta de generalização) com custo
ordens de grandeza menor e **menor variância** da estimativa, sendo a escolha
metodologicamente correta para o volume de dados deste projeto.

---

## 3. Busca de hiperparâmetros (Random Search / Grid Search)

A busca é controlada por flags de CLI e roda **antes** da validação cruzada
final, selecionando os melhores hiperparâmetros do classificador.

### 3.1. Como funciona

1. Opera sobre o **Pipeline** (`imputer → scaler → clf`), variando apenas o
   classificador (chaves com prefixo `clf__`).
2. Usa **`StratifiedKFold`** internamente, otimizando **macro-F1**.
3. Para bases volumosas, a busca roda sobre uma **subamostra estratificada**
   (`--search-sample`, padrão 40.000), e o modelo final é **re-treinado com os
   melhores hiperparâmetros sobre todo o conjunto de treino**. Isso torna a
   busca viável sem comprometer o treino final.
4. Resultados (método, nº de candidatos, melhor CV-F1 e hiperparâmetros
   escolhidos) são **registrados no MLflow**.

### 3.2. Random Search vs Grid Search

| | Random Search (`--search random`) | Grid Search (`--search grid`) |
|---|---|---|
| Como busca | Amostra `n_iter` combinações de distribuições contínuas/discretas | Testa exaustivamente todas as combinações de uma grade discreta |
| Espaço | `*_PARAM_DIST` (config.py) | `*_PARAM_GRID` (config.py) |
| Vantagem | Cobre um espaço amplo com poucas iterações; ideal com muitos hiperparâmetros | Determinístico e completo em grades pequenas |
| Custo | Controlado por `n_iter` | Cresce multiplicativamente com a grade |

**Estratégia escolhida: Random Search como padrão.** O Random Search alcança
boas regiões do espaço com um orçamento fixo de iterações (custo previsível),
sendo mais eficiente que o Grid quando há vários hiperparâmetros. O **Grid
Search permanece disponível** (`--search grid`) para refinamento exaustivo em
uma grade pequena.

### 3.3. Espaços de busca (resumo)

Os espaços são definidos **por modelo** em `config.py` (`PARAM_DIST` para
Random, `PARAM_GRID` para Grid).

**Random Forest** (`random_forest`):

| Hiperparâmetro | Distribuição (random) | Grade (grid) |
|---|---|---|
| `n_estimators` | inteiro em [150, 300) | {200, 300} |
| `max_depth` | inteiro em [14, 30) | {20, 30} |
| `min_samples_leaf` | inteiro em [1, 4) | {1, 2} |
| `max_features` | {sqrt, log2} | — |

**Árvore de Decisão** (`decision_tree`):

| Hiperparâmetro | Distribuição (random) | Grade (grid) |
|---|---|---|
| `max_depth` | inteiro em [10, 45) | {20, 30, None} |
| `min_samples_leaf` | inteiro em [1, 10) | — |
| `criterion` | {gini, entropy} | {gini, entropy} |

> `max_features=None` (todas as features por split) foi deliberadamente
> excluído do Random Forest: é muito lento em bases grandes e não melhora a
> acurácia neste problema.

---

## 4. Como executar

```bash
# A partir da pasta DATAcare, com o venv ativo:
$env:PYTHONPATH = "$PWD\data_pipeline"     # PowerShell (Windows)
# export PYTHONPATH=data_pipeline          # bash (Linux/Mac)

# Random Search (padrão) nos dois modelos
python -m src.models.train --model all

# Grid Search
python -m src.models.train --model all --search grid

# Random Search com mais iterações
python -m src.models.train --model all --search random --n-iter 30

# Sem busca (hiperparâmetros fixos do config.py)
python -m src.models.train --model all --search none

# Dados sintéticos (sem precisar dos parquets reais)
python -m src.models.train --model all --synthetic
```

Flags relevantes:

| Flag | Default | Descrição |
|---|---|---|
| `--search` | `random` | `none` \| `random` \| `grid` |
| `--n-iter` | `12` | nº de combinações do Random Search |
| `--search-cv` | `3` | folds do K-Fold **durante a busca** |
| `--search-sample` | `40000` | tamanho da subamostra da busca (`0` = tudo) |
| `--max-rows` | `400000` | cap de linhas do dataset; `0` = todas |

> A validação cruzada **final** sempre usa 5 folds (`CV_N_SPLITS`),
> independentemente de `--search-cv`.

---

## 5. Rastreamento no MLflow

Cada treino vira um *run* no experimento do modelo
(`datacare-disease-classification` / `datacare-severity-classification`).
Parâmetros registrados ligados à validação/busca:

- `validation` = `holdout + StratifiedKFold`
- `test_size`, `cv_n_splits`, `stratified_split`, `random_state`
- `search_method`, `search_n_candidates`, `search_best_cv_f1`,
  `search_cv_folds`, `search_sample_size`, `search_n_iter`
- hiperparâmetros finais do modelo (já com os melhores valores da busca)

Métricas: `accuracy`, `macro_f1`, `f1_<classe>`, `cv_f1_mean`, `cv_f1_std`.

Abrir a UI para comparar os runs (com e sem busca, random vs grid):

```bash
python -m mlflow ui --backend-store-uri data_pipeline/mlruns
```

---

## 6. Mapeamento ao requisito do projeto

| Item exigido | Atendido? | Como |
|---|---|---|
| Holdout | ✅ | `train_test_split` estratificado 80/20 |
| Validação cruzada | ✅ | `StratifiedKFold` 5-fold + `cross_val_score` (macro-F1) |
| Leave-One-Out (quando aplicável) | ✅ (justificado) | Não aplicável ao volume de dados — ver §2.3 |
| Random Search e/ou Grid Search | ✅ | Ambos implementados (`--search random` / `--search grid`) |
| Justificativa da estratégia | ✅ | Este documento (§2 e §3.2) |

---

## 7. Modelagem: modelos comparados e resultados

### 7.1. Modelos (lista permitida pela disciplina)

Para cada tarefa treinamos e comparamos **2 modelos** (sem XGBoost):

- **Random Forest** (`sklearn.ensemble.RandomForestClassifier`) — ensemble de
  árvores; robusto, lida bem com features mistas e desbalanceamento.
- **Árvore de Decisão** (`sklearn.tree.DecisionTreeClassifier`) — baseline
  interpretável para comparação.

O melhor modelo (por **CV macro-F1**) é salvo em `models/<task>/` para serving.
Os dois ficam registrados como runs separados no MLflow para comparação.

### 7.2. Features

Além de sintomas, comorbidades, dados demográficos e temporais, adicionamos
**features geográficas** (`uf_code`, `munic_code`). Surtos de arboviroses são
fortemente agrupados no espaço-tempo, então a localização é decisiva para
separar dengue/chikungunya/zika (que têm sintomas sobrepostos). Esse foi o fator
que elevou a acurácia do `disease_classifier` de ~87% para ~93%.

### 7.3. Resultados (holdout, dados reais, ≈400k amostras)

| Tarefa | Modelo | Acurácia | Macro-F1 | CV-F1 |
|---|---|---|---|---|
| disease | Árvore de Decisão **(selecionado)** | **0,936** | 0,871 | 0,863 |
| disease | Random Forest | 0,928 | 0,838 | 0,833 |
| severity | Random Forest **(selecionado)** | **0,963** | 0,478 | 0,852 |
| severity | Árvore de Decisão | 0,960 | 0,489 | 0,845 |

**Métricas apropriadas:** reportamos acurácia, **macro-F1** e F1 por classe
(além de matriz de confusão e CV), porque acurácia sozinha engana em bases
desbalanceadas.

> **Ressalva (severity):** a acurácia é alta (96%), mas a **macro-F1 é baixa
> (~0,48)** porque as classes "médio" e "alto" são raríssimas (≈2,4% e ≈0,2%);
> o modelo acerta a classe majoritária "baixo" mas erra muito as graves no
> conjunto de teste (que mantém a distribuição real). O requisito de acurácia
> ≥90% é atendido, mas para uso clínico real a macro-F1/recall das classes
> graves precisaria de mais dados ou ajuste de custo — fica registrado como
> limitação honesta.
