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
— **Random Forest** e **Árvore de Decisão** —
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

> Resultados em dados reais (≈400k amostras, ver §7): **disease ~76,4%** e
> **severity ~99,4%** de acurácia no holdout. A doença é classificada apenas por
> sinais clínicos (sem geografia), o que dá uma acurácia honesta diante de
> sintomas sobrepostos — ver §7.2.

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
| `class_weight` | {balanced, balanced_subsample, None} | {balanced, balanced_subsample} |

**Árvore de Decisão** (`decision_tree`):

| Hiperparâmetro | Distribuição (random) | Grade (grid) |
|---|---|---|
| `max_depth` | inteiro em [10, 45) | {20, 30, None} |
| `min_samples_leaf` | inteiro em [1, 10) | — |
| `criterion` | {gini, entropy} | {gini, entropy} |
| `class_weight` | {balanced, None} | {balanced, None} |

> **`class_weight`** entra na busca para combater o desbalanceamento (dengue
> 73%, "baixo" 97%). O balanceamento ocorre **dentro do estimador, por fold** —
> sem reamostragem prévia (SMOTE), que vazaria pontos sintéticos entre os folds
> e inflaria a validação cruzada.

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

Para cada tarefa treinamos e comparamos **2 modelos**:

- **Random Forest** (`sklearn.ensemble.RandomForestClassifier`) — ensemble de
  árvores; robusto, lida bem com features mistas e desbalanceamento.
- **Árvore de Decisão** (`sklearn.tree.DecisionTreeClassifier`) — baseline
  interpretável para comparação.

O melhor modelo (por **CV macro-F1**) é salvo em `models/<task>/` para serving.
Os dois ficam registrados como runs separados no MLflow para comparação.

### 7.2. Features

**Doença** usa **sintomas + comorbidades + sexo + idade** — sem geografia e sem
features temporais, que seriam *vazamento de alvo* por proveniência:

- **Sem `munic_code`/`uf_code`.** O código do município agiria como proxy do
  rótulo: cada doença é notificada em municípios distintos e a dengue domina o
  volume, então o modelo aprenderia "município ⇒ doença" em vez dos sintomas. No
  SRAG/influenza o município/UF vêm como texto (viram `0`), identificando a
  influenza de forma trivial. A geografia fica como metadado fora de `X`.
- **Idade em anos.** `age_years` é a idade real (de `idade_anos`), um sinal
  clínico legítimo que não domina as importâncias nem identifica o dataset.
- **`class_weight="balanced"`** faz o modelo ponderar as classes e parar de
  "chutar" a majoritária.

**Severidade** usa sintomas + comorbidades + demografia + hospitalização, com o
rótulo "alto" definido por **risco de triagem** (idade ≥ 60, nº de comorbidades,
sinais de alarme — PETEQUIA_N/LEUCOPENIA/LACO — e hospitalização). Para a dengue,
a escala oficial `CLASSI_FIN` (10/11/12) é preservada e *elevada* pelo risco de
triagem. Como o rótulo passa a ser função de sinais conhecidos no atendimento, o
classificador o aprende com alto recall (inclusive na classe "alto").

### 7.3. Resultados (holdout, dados reais, ≈400k amostras)

| Tarefa | Modelo | Acurácia | Balanced acc. | Macro-F1 | CV-F1 |
|---|---|---|---|---|---|
| disease | Random Forest **(selecionado)** | **0,764** | 0,817 | 0,636 | 0,637 |
| disease | Árvore de Decisão | 0,735 | 0,811 | 0,624 | 0,625 |
| severity | Random Forest **(selecionado)** | **0,994** | 0,979 | 0,988 | 0,988 |
| severity | Árvore de Decisão | 0,994 | 0,980 | 0,988 | 0,988 |

**Métricas apropriadas:** reportamos acurácia, **balanced accuracy**, **macro-F1**,
F1 e *recall* por classe (além de matriz de confusão e CV), porque acurácia
sozinha engana em bases desbalanceadas.

> **Acurácia de doença (~76%).** Reflete uma predição dirigida pelos **sintomas**
> (chikungunya clássico → chikungunya, influenza → influenza, sem travar em
> dengue por causa da localização). Como dengue/chikungunya/zika têm sintomas
> sobrepostos — e o parquet de **zika não tem colunas de sintoma** —, esse é o
> teto realista para uma classificação clínica honesta.
>
> **CV honesta.** O balanceamento por `class_weight` ocorre dentro de cada fold,
> então `cv_f1_mean ≈ macro_f1` de teste em ambas as tarefas — a validação
> cruzada estima fielmente o desempenho real. Na severidade, o recall da classe
> "alto" fica em **~0,95**, graças à definição por risco de triagem.
