# Tratamento de Dados e ETL — DATAcare

Este documento explica **tudo o que acontece com os dados** desde o CSV bruto do
SUS até as matrizes de features que alimentam os modelos. É a referência técnica
do pipeline de **E**xtração, **T**ransformação e **L**oad (ETL) e do
*feature engineering*.

> Código de referência: `data_pipeline/src/etl/` (limpeza + split) e
> `data_pipeline/src/features/` (feature engineering).
> Para *como rodar*, veja [`EXECUCAO.md`](./EXECUCAO.md).

---

## Índice

1. [Visão geral do fluxo](#1-visão-geral-do-fluxo)
2. [Fontes de dados](#2-fontes-de-dados)
3. [Extração: leitura dos CSVs](#3-extração-leitura-dos-csvs-em-chunks)
4. [Transformação: a limpeza](#4-transformação-a-limpeza)
5. [Load intermediário: parquet](#5-load-intermediário-por-que-parquet)
6. [Split treino/validação/teste](#6-split-treinovalidaçãoteste)
7. [Validação anti-vazamento (leakage)](#7-validação-anti-vazamento-leakage)
8. [Feature engineering](#8-feature-engineering)
9. [Relatórios gerados](#9-relatórios-gerados)
10. [Reprodutibilidade e extensão](#10-reprodutibilidade-e-extensão)

---

## 1. Visão geral do fluxo

```
CSV bruto (SUS)                  TRANSFORMAÇÃO                  ARTEFATOS
─────────────────   ┌─────────────────────────────────┐   ──────────────────────
Dados/*.csv  ──────▶ │ 1. Extração (leitura em chunks) │
(~870 MB, latin-1)   │ 2. Limpeza (encoding, datas,    │ ──▶ interim/*.parquet
                     │    códigos, dedup)              │     (1 por dataset, ~12× menor)
                     │ 3. Split (temporal anti-leakage)│ ──▶ processed/{train,val,test}/
                     │ 4. Validação anti-vazamento     │ ──▶ reports/{cleaning,leakage}/
                     └─────────────────────────────────┘
                                     │
                                     ▼
                     feature engineering (src/features) ──▶ matrizes (X, y) p/ os modelos
```

Os passos 1–4 são o **ETL** (`python -m src.etl.run_pipeline`). O feature
engineering roda **dentro do treino**, lendo os parquets limpos de `interim/`.

---

## 2. Fontes de dados

O pipeline ativo processa **4 datasets** — os que alimentam os classificadores
de doença e severidade:

| Dataset (slug) | Arquivo bruto | Família | Tamanho CSV | Separador |
|----------------|---------------|---------|-------------|-----------|
| `sinan_dengue` | `dengue_2025.csv` | SINAN (caso notificado) | ~436 MB | `,` |
| `sinan_chikungunya` | `chikungunya_2025.csv` | SINAN (caso notificado) | ~67 MB | `,` |
| `sinan_zika` | `zika_2025.csv` | SINAN (caso notificado) | ~4 MB | `,` |
| `srag_influenza` | `influeza_srag_2025.csv` | SRAG (SIVEP-Gripe) | ~364 MB | `;` |

Cada fonte é descrita por um `DatasetSpec` em
`data_pipeline/src/etl/config.py` (nome do arquivo, separador, encoding, colunas
de data, coluna temporal, colunas "sim/não", estratégia de split). **Adicionar
uma nova fonte é uma única entrada nesse dicionário** — todo o resto do pipeline
se adapta.

> **Sobre PNS e taxas de incidência.** O código traz *cleaners* específicos para
> a PNS 2019 (`pns.py`, survey clusterizado) e para taxas de incidência
> agregadas (`taxa_incid.py`). Eles **não estão no conjunto ativo `DATASETS`**
> hoje, porque os modelos atuais (doença e severidade) usam apenas SINAN e SRAG.
> Os cleaners permanecem no repositório como base pronta para análises
> epidemiológicas futuras.

> Arquivos `sinannet_*_2025.csv` (1–3 KB) são apenas cabeçalhos de relatório
> TabWin, sem dados — ignorados. PDFs/planilhas de dicionário ficam como
> referência, fora do ETL.

---

## 3. Extração: leitura dos CSVs em chunks

Os CSVs brutos somam quase 1 GB; carregá-los inteiros em memória estoura a RAM.
Por isso **toda leitura é feita em pedaços** (`iter_chunks` em
`data_pipeline/src/etl/io_utils.py`):

- **Chunks de 100.000 linhas** (`DEFAULT_CHUNKSIZE`) — processa um pedaço,
  libera memória, lê o próximo.
- **Tudo entra como `string` (`dtype=str`)**: os tipos corretos são derivados
  *na limpeza*, evitando que o pandas adivinhe tipos errados (e perca zeros à
  esquerda de códigos, por exemplo).
- **Encoding `latin-1`** forçado em todos os CSVs do SUS — sem isso há *mojibake*
  (acentuação corrompida), confirmado nos dados reais.
- **`on_bad_lines="warn"`**: linhas malformadas geram aviso em vez de derrubar
  a leitura inteira.
- **`--sample N`** lê apenas as N primeiras linhas de cada arquivo (modo
  dry-run) — essencial para validar o pipeline em ~1 min antes de processar tudo.

---

## 4. Transformação: a limpeza

A limpeza é organizada em **cleaners** (`data_pipeline/src/etl/cleaners/`). Um
`BaseCleaner` implementa as primitivas comuns e cada família estende com regras
próprias:

| Cleaner | Família | Especializações |
|---------|---------|-----------------|
| `BaseCleaner` | — | strings, datas, códigos sim/não, sentinelas, dedup |
| `SinanCleaner` | SINAN | idade composta, `CS_SEXO`, IDs IBGE como string |
| `SragCleaner` | SRAG | idade preferindo `DT_NASC`, esquema SIVEP |
| `PnsCleaner` | PNS | preserva `UPA_PNS`, `V0001`, pesos amostrais |
| `TaxaIncidCleaner` | taxa_incid | indicadores numéricos + competência mensal |

### 4.1. Primitivas do `BaseCleaner` (aplicadas a todos)

1. **Normalização de strings** (`_strip_strings`)
   `strip()` em todas as colunas de texto e conversão de *sentinelas de
   ausência* (`""`, `"nan"`, `"none"`, `"null"`, `"nat"`, `"na"`, `"-"`) para
   `NA`. Sem isso, um literal `"nan"` vindo da fonte seria tratado como texto
   válido e contaminaria datas, deduplicação e split.

2. **Parsing de datas** (`_parse_dates`)
   Tenta primeiro o formato **ISO** (rápido). Para as linhas que falharam,
   reprocessa a string original com `format="mixed", dayfirst=True`, recuperando
   o padrão brasileiro **DD/MM/AAAA** mesmo quando a coluna mistura ISO + BR.
   Sem o passo `mixed`, o pandas 2.x rejeitaria o lote inteiro e devolveria
   `NaT` para tudo — perda silenciosa do sinal temporal (que é a base do split).
   Linhas com data inválida são **contadas** no relatório.

3. **Recodificação de códigos sim/não/ignorado** (`_recode_yes_no`)
   No padrão SINAN/SRAG, sintomas e comorbidades vêm como `1=sim`, `2=não`,
   `9=ignorado`. Convertemos para o tipo booleano do pandas:
   `{1 → True, 2 → False, 9 → NA}`. Reduz ambiguidade e cardinalidade, e deixa o
   "ignorado" explicitamente ausente (não confundível com "não").

4. **Sentinelas numéricas** (`_replace_sentinels`)
   Códigos de preenchimento (`99`, `999`, `9999`) em colunas numéricas viram
   `NaN` quando declarados em `numeric_sentinel_columns`.

5. **Deduplicação em duas camadas** (`_drop_exact_duplicates` + passe global)
   - *Por chunk:* remove duplicatas exatas durante o processamento (economiza
     memória).
   - *Global:* após concatenar todos os chunks, um `drop_duplicates` final pega
     duplicatas que **cruzam fronteiras de chunk** — invisíveis na camada por
     chunk. Sem essa segunda camada, dois registros idênticos em chunks
     distintos sobreviveriam e dispararia um **falso positivo de vazamento** no
     split.

### 4.2. Regras específicas do SINAN (`SinanCleaner`)

- **Idade composta `NU_IDADE_N` → `idade_anos`.** O SINAN codifica idade num
  número de 4 dígitos: o **primeiro dígito é a unidade** (`1=hora`, `2=dia`,
  `3=mês`, `4=ano`) e os **3 últimos, o valor**. Exemplos: `4023 = 23 anos`,
  `3006 = 6 meses`, `2014 = 14 dias`. Convertendo tudo para anos
  (`6 meses → 0,5`), idades > 130 anos viram `NaN` (código inválido).
- **`CS_SEXO`** normalizado para `{M, F, I}`; qualquer outro valor → `NA`.
- **IDs IBGE** (`ID_MUNICIP`, `SG_UF_NOT`, `ID_REGIONA`, `CO_MUN_*`, etc.)
  mantidos como **`string`** para preservar zeros à esquerda — números perderiam
  o `0` inicial e quebrariam o cruzamento geográfico.

### 4.3. Regras específicas do SRAG (`SragCleaner`)

- **Idade preferindo `DT_NASC`.** Quando há data de nascimento, a idade é
  calculada como `(DT_NOTIFIC − DT_NASC) / 365.25`. Só usa o `NU_IDADE_N`
  composto como **fallback** quando `DT_NASC` está ausente.
- Esquema próprio do SIVEP-Gripe (colunas de UTI, antiviral, vacinação, PCR) e a
  mesma normalização de sexo e de IDs.

### 4.4. Resumo das transformações

| Aspecto | Tratamento |
|---------|-----------|
| Encoding | `latin-1` forçado (corrige *mojibake*) |
| Strings vazias / sentinelas | `→ NA` |
| Datas | ISO + fallback `dayfirst` para DD/MM/AAAA |
| Idade (SINAN) | `NU_IDADE_N` composto → `idade_anos` |
| Idade (SRAG) | `DT_NASC` preferida; `NU_IDADE_N` fallback |
| Sexo | normalizado para `{M, F, I}` |
| Sim/Não/Ignorado | `BooleanDtype` `{True, False, NA}` |
| Sentinelas numéricas | `99/999/9999 → NaN` |
| IDs IBGE | mantidos como `string` (zeros à esquerda) |
| Duplicatas exatas | removidas (por chunk + global) e contadas |

---

## 5. Load intermediário: por que parquet

Cada dataset limpo é gravado como **um arquivo Parquet** em
`data_pipeline/data/interim/`. Parquet em vez de CSV porque:

- **Colunar e comprimido** — os 4 CSVs (~870 MB) viram ~69 MB de parquet
  (**redução de ~12×**). Leitura e escrita muito mais rápidas.
- **Preserva tipos** — booleanos, datas e strings sobrevivem ao *round-trip*
  (CSV perderia toda a tipagem feita na limpeza, exigindo re-inferência).
- **Particionamento natural** — o split grava um parquet por partição
  (`train/val/test`), e o feature engineering lê só o que precisa.

---

## 6. Split treino/validação/teste

Depois de limpar, cada dataset é separado em **treino (70%) / validação (15%) /
teste (15%)** (`SplitRatios` em `config.py`). A **estratégia de split** é
escolhida por dataset, conforme a *unidade de observação* e o que o modelo
precisa generalizar (`data_pipeline/src/etl/splitters/strategies.py`):

| Estratégia | Quando usar | Como funciona |
|------------|-------------|---------------|
| **Temporal** (ativa hoje) | Séries de vigilância (SINAN, SRAG) | Ordena por data e corta cronologicamente: `train < val < test` no tempo |
| **Grouped** | Surveys clusterizados (PNS por UPA) | Todos os registros de um mesmo grupo caem no mesmo split |
| **StratifiedTemporal** | Alvos desbalanceados em série temporal | Temporal + diagnóstico de balanceamento por janela |

### 6.1. Por que split temporal (e não aleatório)?

Em produção, o modelo só vê notificações **futuras**. Um split aleatório deixaria
o modelo "ver o futuro" durante o treino (vazamento de padrões sazonais),
inflando artificialmente as métricas. O split temporal replica o cenário real:
treina no passado, valida/testa no futuro.

| Dataset | Estratégia | Coluna decisiva | Por quê |
|---------|-----------|-----------------|---------|
| SINAN dengue/chik/zika | temporal | `DT_NOTIFIC` | Em deployment só há notificações futuras; split aleatório vazaria sazonalidade |
| SRAG/Influenza | temporal | `DT_NOTIFIC` | Mesmo motivo — vigilância é série temporal |

### 6.2. Tratamento de bordas

- **Datas inválidas** (`NaT`): não dá para ordenar no tempo, então essas linhas
  vão para o **treino** (sem risco de vazamento cronológico; descartá-las
  perderia sinal).
- **Fallback de estratégia:** datasets temporais podem declarar
  `fallback_group_column`. Se a coluna temporal chegar 100% inválida (caso real:
  `taxa_indic_chikungunya.csv` traz `co_anomes` como string `"nan"`), o pipeline
  **cai automaticamente para split por grupo** (ex.: por município), logando um
  WARNING — preservando o anti-vazamento geográfico mesmo sem o eixo temporal.

---

## 7. Validação anti-vazamento (leakage)

Vazamento (*data leakage*) é quando informação do teste "vaza" para o treino,
produzindo métricas otimistas que não se sustentam em produção. Após **cada**
split, um validador (`data_pipeline/src/etl/splitters/leakage.py`) roda
automaticamente e grava `reports/leakage/<dataset>.json`. Ele checa:

1. **`duplicate_rows_across_splits`** — nenhuma linha (hash de todas as colunas)
   aparece em mais de um split. Verifica **cada par** de splits não-vazios.
2. **`group_overlaps`** — em splits por grupo, nenhuma chave de grupo
   (UPA, paciente, município) é compartilhada entre splits.
3. **`temporal_order_ok`** — em splits temporais, garante
   `max(train) < min(val) < min(test)` (ordem cronológica estrita).
4. **`ratios`** — as proporções saíram dentro da tolerância de 5 p.p.

> Se qualquer um dos **três primeiros** falhar, o split é considerado contaminado
> e o CLI sai com **exit code 1** — o pipeline aborta antes de qualquer treino.
> Proporção fora da tolerância gera apenas *warning*.

---

## 8. Feature engineering

O feature engineering (`data_pipeline/src/features/`) transforma os parquets
limpos nas matrizes `(X, y)` que os modelos consomem. A configuração de colunas e
rótulos é **fonte única** em `data_pipeline/src/features/config.py`.

### 8.1. Grupos de features

| Grupo | Exemplos | Origem |
|-------|----------|--------|
| Sintomas (SINAN) | `FEBRE`, `MIALGIA`, `EXANTEMA`, `ARTRALGIA`, `PETEQUIA_N`, ... | colunas booleanas limpas |
| Sintomas (SRAG) | `FEBRE`, `TOSSE`, `DISPNEIA`, `DIARREIA`, ... | colunas booleanas limpas |
| Comorbidades | `DIABETES`, `RENAL`, `HIPERTENSA`, `CARDIOPATI`, ... | colunas booleanas limpas |
| Demográficas | `age_years` (de `idade_anos`), `sex_M` (de `CS_SEXO`) | derivadas |
| Temporais | `notification_month`, `notification_week` (de `DT_NOTIFIC`) | derivadas (só severidade) |
| Geográficas | `uf_code`, `munic_code` | **só metadado — fora dos modelos** |

> **Por que NÃO usamos geografia nos modelos.** O código do município
> (`munic_code`) seria um *vazamento de alvo*: cada doença é notificada em
> municípios distintos e a dengue domina o volume, então o município agiria como
> proxy quase perfeito do arquivo de origem — o modelo aprenderia "município ⇒
> doença" em vez dos sintomas, travando a predição na classe majoritária. No
> SRAG/influenza o município/UF vêm como texto, o que ainda identificaria a
> classe trivialmente. Por isso a geografia fica como **metadado** (para o
> dashboard), fora de `X`. A idade entra como `idade_anos` (idade real em anos),
> um sinal clínico legítimo que não identifica o dataset.

### 8.2. Classificador de doença (`build_disease_features`)

Combina os três SINAN + o SRAG, atribuindo o rótulo de doença:

| Rótulo | Classe | Fonte |
|--------|--------|-------|
| 0 | dengue | `sinan_dengue` |
| 1 | chikungunya | `sinan_chikungunya` |
| 2 | zika | `sinan_zika` |
| 3 | influenza | `srag_influenza` |

### 8.3. Classificador de severidade (`build_severity_features`)

A severidade (`0=baixo`, `1=medio`, `2=alto`) é derivada de forma diferente por
doença, refletindo como cada sistema codifica gravidade:

A severidade é um **nível de risco de triagem**, derivado de sinais conhecidos
no atendimento — e que o dashboard envia ao modelo:

- **médio (1):** qualquer fator de risco — idoso (≥60 anos), ≥1 comorbidade,
  sinal de alarme (`PETEQUIA_N`/`LEUCOPENIA`/`LACO`) ou hospitalização.
- **alto (2):** hospitalizado **E** com agravante (idoso, ≥2 comorbidades ou
  sinal de alarme).
- **Dengue:** preserva a escala oficial `CLASSI_FIN` (`10→baixo`, `11→médio`,
  `12/13→alto`) e a **eleva** pelo risco de triagem (máximo entre as duas).

> **Por que por triagem.** Definir "alto" por sinais previsíveis no atendimento
> (em vez de desfechos como óbito/`EVOLUCAO`, que não entram como feature) alinha
> o rótulo às variáveis disponíveis — o modelo consegue aprendê-lo, com recall de
> "alto" em ~0,95.

> **Desbalanceamento.** O balanceamento usa **`class_weight="balanced"`** dentro
> do estimador (por fold), em vez de reamostragem prévia (SMOTE) — que vazaria
> pontos sintéticos entre os folds e inflaria a validação cruzada. As
> implicações nas métricas estão em
> [`VALIDACAO.md`](./VALIDACAO.md#73-resultados-holdout-dados-reais-400k-amostras).

### 8.4. Dados sintéticos

`make_synthetic_disease` e `make_synthetic_severity` geram dados artificiais com
sinais epidemiologicamente plausíveis (ex.: chikungunya com artrite/artralgia
alta; alto risco em idosos com comorbidades hospitalizados). Servem para
**testes unitários e CI** e para rodar o treino em qualquer máquina **sem os
parquets reais** — o treino cai para eles automaticamente quando os parquets não
existem.

---

## 9. Relatórios gerados

Cada execução do ETL deixa um rastro auditável em JSON
(`data_pipeline/data/reports/`):

### 9.1. Relatório de limpeza (`reports/cleaning/<dataset>.json`)

```json
{
  "dataset": "sinan_zika",
  "source_file": "zika_2025.csv",
  "raw_rows": 5000,
  "cleaned_rows": 4995,
  "duplicates_dropped": 5,
  "rows_with_invalid_dates": 12,
  "yes_no_columns_recoded": ["FEBRE", "MIALGIA", "..."],
  "date_columns_parsed": ["DT_NOTIFIC", "DT_SIN_PRI", "..."],
  "notes": ["..."]
}
```

### 9.2. Relatório de vazamento (`reports/leakage/<dataset>.json`)

Traz `strategy`, `sizes`, `ratios`, `duplicate_rows_across_splits`,
`group_overlaps`, `temporal_order_ok`, além de `errors`/`warnings`.

Esses relatórios também alimentam o **dashboard Streamlit** (página *ETL &
Qualidade de Dados*).

---

## 10. Reprodutibilidade e extensão

- **Seed única** `RANDOM_SEED = 42` em `config.py` controla toda escolha
  aleatória (splits por grupo, embaralhamentos) — execuções repetidas dão o
  mesmo resultado.
- **Configuração centralizada** — datasets, separadores, encoding, colunas e
  estratégia de split vivem no dicionário `DATASETS`. Não há *magic strings*
  espalhadas pelo código.
- **Adicionar uma nova fonte** = adicionar **uma entrada** em `DATASETS` (e, se
  o esquema for novo, um cleaner que estenda `BaseCleaner`). O orquestrador, o
  split e a validação anti-vazamento passam a cobri-la automaticamente.

> Para a parte de modelagem (algoritmos, validação cruzada, busca de
> hiperparâmetros e resultados), veja [`VALIDACAO.md`](./VALIDACAO.md).
> Para conteinerização e MLflow, veja [`DOCKER_ML.md`](./DOCKER_ML.md).
