# Branch `feature/data-cleaning-split` — Limpeza e Particionamento dos Dados

> Documento de handoff. Lê este se você vai revisar, continuar ou simplesmente entender o que esta branch entregou.

---

## Sumário

1. [Contexto](#1-contexto)
2. [O que esta branch entrega](#2-o-que-esta-branch-entrega)
3. [Estrutura do código novo](#3-estrutura-do-código-novo)
4. [Decisões técnicas importantes](#4-decisões-técnicas-importantes)
5. [Como rodar](#5-como-rodar)
6. [Como verificar que funcionou](#6-como-verificar-que-funcionou)
7. [Bugs corrigidos durante o desenvolvimento](#7-bugs-corrigidos-durante-o-desenvolvimento)
8. [Limitações conhecidas / dados problemáticos](#8-limitações-conhecidas--dados-problemáticos)
9. [Próximos passos](#9-próximos-passos)
10. [Apêndice: glossário rápido](#10-apêndice-glossário-rápido)

---

## 1. Contexto

### Branch
- **Nome:** `feature/data-cleaning-split`
- **Derivada de:** `feature/data-etl`
- **Escopo:** transformar os CSVs brutos do SUS (em `Dados/`) em datasets limpos, tipados e particionados em treino/validação/teste, com checagem automática contra contaminação entre subconjuntos.

### Onde a branch se encaixa nas Histórias de Usuário
A branch é a base do **T**ransform do ETL declarado na HU-07 (*Pipeline de Dados Automático*) e o pré-requisito direto da HU-04 (*EDA*), HU-05 (*Feature Engineering*) e HU-06 (*Modelo ML*). Sem dados limpos e particionados corretamente, qualquer trabalho de modelagem acumularia vícios silenciosos.

### Por que separar limpeza de split em uma branch própria
Limpeza e particionamento têm decisões muito diferentes: limpeza lida com tipos e nulos; split lida com prevenção de leakage. Misturar os dois força um único cleaner a entender também o desenho amostral, o que cresce mal quando outras fontes forem adicionadas. Aqui ficam módulos isolados que conversam por arquivos Parquet.

---

## 2. O que esta branch entrega

### Datasets tratados (8)

| Família       | Slug                          | Arquivo bruto                  | Estratégia de split             |
|---------------|-------------------------------|--------------------------------|---------------------------------|
| SINAN caso    | `sinan_dengue`                | `dengue_2025.csv`              | temporal por `DT_NOTIFIC`       |
| SINAN caso    | `sinan_chikungunya`           | `chikungunya_2025.csv`         | temporal por `DT_NOTIFIC`       |
| SINAN caso    | `sinan_zika`                  | `zika_2025.csv`                | temporal por `DT_NOTIFIC`       |
| SRAG          | `srag_influenza`              | `influeza_srag_2025.csv`       | temporal por `DT_NOTIFIC`       |
| PNS microdados| `pns_2019`                    | `pns2019.csv`                  | grouped por `UPA_PNS`           |
| Taxa agregada | `taxa_incid_dengue`           | `taxa_incid_dengue.csv`        | temporal por `co_anomes`        |
| Taxa agregada | `taxa_incid_zika`             | `taxa_incid_zika.csv`          | temporal por `co_anomes`        |
| Taxa agregada | `taxa_incid_chikungunya`      | `taxa_indic_chikungunya.csv`   | **fallback** grouped por `co_ibge` |

**Não entram no ETL** (mas vivem em `Dados/`):
- `sinannet_*_2025.csv` (1–3 KB cada): cabeçalhos de relatórios TabWin, sem dados.
- `dic_dados_*.pdf` e `dicionario_PNS_microdados_2019_23062023.xls`: dicionários de variáveis — referência para análise, não dados.

### Artefatos gerados

```
data_pipeline/data/
├── interim/                  # 1 parquet limpo por dataset (antes do split)
├── processed/{train,val,test}/    # parquet particionado, consumível pelo ML
└── reports/
    ├── cleaning/<dataset>.json   # contagens, colunas recodificadas, datas parseadas
    └── leakage/<dataset>.json    # checagem anti-contaminação (errors:[] = OK)
```

### Testes
- **31 testes** em `data_pipeline/tests/etl/` (pytest). Rodam em <1 s, sem dependências externas:
  - 11 testes de cleaners (decodificação de idade SINAN, recode 1/2/9, preservação de IDs, fallback de idade no SRAG, etc.).
  - 19 testes de splitters (ordem temporal estrita, ausência de overlap de grupos, validador detectando leakage *injetado de propósito*, etc.).
  - 1 teste do fallback de split (reproduz exatamente o caso `taxa_indic_chikungunya.csv`).

### Memória do projeto
Três notas persistidas em `~/.claude/projects/.../memory/` para que conversas futuras já cheguem com o contexto:
- `feedback_no_auto_commit.md` — não commitar sem autorização explícita.
- `project_datacare.md` — escopo do projeto e onde mora cada coisa.
- `project_dados_brutos.md` — catálogo dos CSVs brutos com formato/encoding.

---

## 3. Estrutura do código novo

Tudo abaixo de `DATAcare/data_pipeline/`:

```
data_pipeline/
├── README.md                          # guia de uso operacional
├── src/
│   ├── etl/
│   │   ├── config.py                  # caminhos + DatasetSpec por fonte
│   │   ├── io_utils.py                # leitura em chunks, escrita parquet
│   │   ├── clean.py                   # CLI: bruto → interim/
│   │   ├── split.py                   # CLI: interim/ → processed/{train,val,test}/
│   │   ├── run_pipeline.py            # CLI orquestrador (clean + split)
│   │   ├── cleaners/
│   │   │   ├── base.py                # parsing datas, recode 1/2/9, dedup, sentinelas
│   │   │   ├── sinan.py               # SINAN clássico (dengue/chik/zika)
│   │   │   ├── srag.py                # SRAG/Influenza
│   │   │   ├── pns.py                 # PNS 2019 microdados
│   │   │   └── taxa_incid.py          # taxas agregadas
│   │   └── splitters/
│   │       ├── strategies.py          # TemporalSplitter, GroupedSplitter, StratifiedTemporalSplitter
│   │       └── leakage.py             # validador anti-contaminação
│   └── utils/logging_config.py
├── data/                              # outputs (vide §2)
└── tests/etl/
    ├── test_cleaners.py
    └── test_splitters.py
```

---

## 4. Decisões técnicas importantes

### 4.1. Parquet em vez de CSV

Saída de todas as etapas é **Parquet**. Quatro razões:

1. **Tamanho**: 5–10× menor que o CSV equivalente (boolean = 1 byte/linha, dictionary encoding de UFs/códigos repetidos).
2. **Tipos preservados**: `boolean`, `datetime64`, `float64`, `string` ficam gravados — não precisa reparsear data nem recodificar Sim/Não a cada vez que abre.
3. **Leitura colunar**: `pd.read_parquet(path, columns=[...])` lê só o que precisa do disco. CSV obriga a varrer tudo.
4. **Padrão de mercado**: pandas, sklearn, xgboost, polars e Spark consomem Parquet nativamente.

Trade-off: Parquet é binário, não abre em Notepad/Excel. Para inspeção humana use **Data Wrangler** (extensão VS Code, Microsoft) ou **Tad Viewer** (binário standalone).

### 4.2. Estratégias de split escolhidas por *unidade de observação*

A escolha do split **não é gosto pessoal** — depende de como o modelo será usado em produção.

| Dataset                  | Unidade de obs. | Estratégia       | Justificativa                                                                                                                          |
|--------------------------|------------------|------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| SINAN dengue/chik/zika   | notificação      | temporal         | Em deployment, o modelo só vê *notificações futuras*. Split aleatório vazaria padrões sazonais (e.g. epidemia de janeiro) entre splits. |
| SRAG/Influenza           | notificação      | temporal         | Mesmo motivo — surveillance é uma série temporal estrita.                                                                              |
| PNS 2019                 | indivíduo numa UPA | grouped por UPA  | Survey clusterizado: respondentes da mesma UPA são correlacionados por desenho amostral. Quebrar uma UPA entre splits = leakage por cluster. |
| Taxa de incidência       | município × mês  | temporal         | Mesmo município repete a cada mês. Split aleatório vazaria autocorrelação espaço-temporal e o test "vê o futuro do treino".            |

### 4.3. Como a limpeza funciona, passo a passo

`BaseCleaner.run()` orquestra a sequência abaixo. Cada cleaner concreto (SINAN/SRAG/PNS/Taxa) estende com regras específicas, mas o esqueleto é o mesmo.

1. **Leitura em chunks** (`io_utils.iter_chunks`)
   - `pd.read_csv` em blocos de 100 mil linhas com `dtype=str` (tudo string na entrada), `encoding="latin-1"`, `separator` e `quoting` do `DatasetSpec`.
   - `na_values=["", " ", "NA", "NaN", "null"]` + `keep_default_na=True` — pandas já converte esses tokens para NaN no parse.
   - `on_bad_lines="warn"` — linhas mal-formadas (campo extra/faltando) são puladas com warning no stderr.
2. **Normalização de strings** (`_strip_strings`)
   - `str.strip()` em todas as colunas object.
   - Strings-sentinela `"nan" / "none" / "null" / "nat" / "na" / "-"` (case-insensitive) viram `pd.NA`. Sem essa etapa, datasets que publicam `"nan"` literal (caso `taxa_indic_chikungunya`) silenciosamente sobreviveriam à limpeza.
3. **Parsing de datas** (`_parse_dates`, sobre `spec.date_columns`)
   - Salva a string original antes de qualquer coerção.
   - Primeira tentativa: `pd.to_datetime(dayfirst=False)` — rápido para ISO `AAAA-MM-DD`.
   - Se sobraram NaTs novos: segunda tentativa com `format="mixed", dayfirst=True` sobre a string original — recupera `DD/MM/AAAA` mesmo em colunas com formato misto. (Sem `format="mixed"`, pandas 2.0+ rejeita o lote misto e retorna NaT pra tudo que não é ISO.)
   - `fillna` aplica a segunda nas linhas que falharam na primeira.
4. **Recode Sim/Não/Ignorado** (`_recode_yes_no`, sobre `spec.yes_no_columns`)
   - SINAN/SRAG usam `1=Sim, 2=Não, 9=Ignorado`. O cleaner mapeia para `{True, False, pd.NA}` e força `BooleanDtype`. Resultado: dtype semanticamente correto, NA explícito.
5. **Sentinelas numéricas** (`_replace_sentinels`, opcional)
   - Quando `spec.numeric_sentinel_columns` está setado, valores em `spec.sentinels` (default `99, 999, 9999`) viram `NaN` nas colunas indicadas. Útil pra evitar que sentinelas DataSUS virem outliers no modelo.
6. **Dedup intra-chunk** (`_drop_exact_duplicates`)
   - `drop_duplicates` por chunk — barato e reduz memória antes da concatenação. Não pega duplicatas que cruzam fronteiras de chunk; isso é tratado no passo 9.
7. **Regras específicas da subclasse** (extensões via `super()` ou substituição completa)
   - **SinanCleaner**: normaliza `CS_SEXO` (M/F/I), decodifica `NU_IDADE_N` composto para `idade_anos` em anos, mantém IDs IBGE como `StringDtype`.
   - **SragCleaner**: idem, mas prefere `DT_NASC` quando disponível (idade mais confiável que `NU_IDADE_N`).
   - **PnsCleaner**: preserva `UPA_PNS` e demais variáveis de desenho amostral como string; detecta colunas de peso.
   - **TaxaIncidCleaner**: tipa indicadores numéricos `vl_indicador_calculado_*`, parseia `dt_competencia` e `dt_atualizacao`.
8. **Concatenação** (`pd.concat(frames, ignore_index=True)`)
   - Junta todos os chunks limpos em um único DataFrame.
9. **Dedup global** (`df.drop_duplicates`)
   - Segunda camada de deduplicação, agora vendo o dataset inteiro. Pega duplicatas que estavam em chunks diferentes. Sem essa camada, dois registros idênticos disparariam falso erro de "leakage" no split. `report.notes` registra quantas duplicatas foram pegas só aqui.
10. **Escrita** (`to_parquet`)
    - Saída em `data/interim/<dataset>.parquet`, sem index. Parquet preserva os dtypes definidos acima (boolean, datetime64, float, string).
11. **Relatório** (`CleaningReport.write`)
    - JSON em `data/reports/cleaning/<dataset>.json` com `raw_rows`, `cleaned_rows`, `duplicates_dropped`, colunas recodificadas, datas parseadas e notas.

### 4.4. Como o split funciona, passo a passo

O `DatasetSpec.split_strategy` define qual splitter aplicar; `split.py` materializa em três Parquets e o validador roda em cima.

#### TemporalSplitter (SINAN, SRAG, taxa_incid)

1. **Verifica a coluna de tempo** (`spec.time_column`, e.g. `DT_NOTIFIC` ou `co_anomes`). Se ausente do DataFrame → `ValueError`.
2. **Detecta linhas válidas**: `mask_valid = df[time].notna()`.
3. **Fallback espacial** (em `split.py:_splitter_with_fallback`): se `notna().sum() == 0` e o spec declara `fallback_group_column` (caso real do `taxa_indic_chikungunya` onde `co_anomes` chega todo NaN da fonte), cai para `GroupedSplitter` na coluna geográfica. Anti-leakage por município substitui anti-leakage temporal. Loga WARNING explícito.
4. **Ordenação cronológica**: `argsort(kind="mergesort")` sobre a coluna de tempo, preservando estabilidade nos empates.
5. **Corte por posição**: `n_train = int(N * ratios.train)`, idem val. As fatias `iloc[:n_train]`, `iloc[n_train:n_train+n_val]`, `iloc[n_train+n_val:]` viram train/val/test. Treino fica sempre com as datas mais antigas; test sempre com as mais recentes.
6. **Linhas com tempo NaT**: anexadas no **train** via `pd.concat`. Não dá pra alocá-las cronologicamente; descartar perderia sinal. (Trade-off: pode inflar train em datasets esparsos.)
7. Retorna `SplitResult(train, val, test)`.

#### GroupedSplitter (PNS, fallback do chikungunya)

1. **Cast da chave de grupo** para `StringDtype` (preserva zeros à esquerda de códigos IBGE/UPA).
2. **Lista de grupos únicos**: `groups.dropna().unique()`.
3. **Modo estratificado** (quando `stratify_column` declarada e presente no df, como PNS+UF):
   - Calcula a classe modal de cada grupo (`groupby(group_column)[stratify_column].agg(mode)`).
   - Embaralha grupos **dentro de cada classe** com seed fixa.
   - Para cada classe, fatia 70/15/15 dos grupos e une nos sets `train_g/val_g/test_g`.
   - Grupos sem classe (NaN) caem num bucket à parte, splittados aleatoriamente.
   - Se `stratify_column` declarada mas ausente do df → loga WARNING e cai para split aleatório (visibilidade explícita, não silencioso).
4. **Modo aleatório** (default): embaralha todos os grupos e fatia 70/15/15.
5. **Partição do DataFrame**: `df[groups.isin(train_g)]`, idem val/test. **Todas as linhas de um mesmo grupo caem juntas** — invariante central do split por cluster.
6. **Linhas com grupo NaN**: anexadas no train (mesma lógica do TemporalSplitter para NaTs).
7. Retorna `SplitResult(train, val, test)`.

Note que o número de **linhas** por split pode divergir das proporções alvo (70/15/15 vira ~69/15/17 no PNS) porque grupos têm tamanhos variáveis. As proporções de **grupos** estão certas; o número de linhas é um efeito do desenho amostral. Sem isso, anti-leakage seria impossível.

### 4.5. O validador anti-leakage

Após **todo** split, `splitters/leakage.py` checa quatro coisas e grava um JSON em `data/reports/leakage/`. Se algum item falhar com severidade alta, o CLI sai com exit code ≠ 0:

1. **Nenhuma linha idêntica** entre quaisquer dois splits não-vazios — hasheia todas as colunas com `pd.util.hash_pandas_object` e calcula interseção dos hashes. Trata `pd.NA` consistentemente em qualquer dtype.
2. **Nenhuma chave de grupo** (UPA, paciente, município) compartilhada em pares de splits — só relevante para grouped.
3. **Ordem temporal estrita**: para os splits presentes (não-vazios e com tempo válido), `max(prev) > min(next)` é erro. Quando val está vazio (por config ou dataset esparso), train↔test continua sendo comparado diretamente — antes essa comparação era silenciosamente pulada.
4. **Proporções dentro da tolerância** (default ±5 p.p.). Acima disso, vira warning, não erro.

O validador é o "freio de mão" do pipeline. Sem ele, um bug no split passaria despercebido até o modelo treinar e mostrar métricas suspeitamente boas — depois suspeitamente ruins em produção.

### 4.6. Decodificação composta de idade (SINAN/SRAG)

O campo `NU_IDADE_N` do SINAN é numérico de 4 dígitos onde o primeiro dígito é a unidade (1=hora, 2=dia, 3=mês, 4=ano) e os 3 últimos são o valor. Exemplos:

- `4023` → 23 anos
- `3006` → 6 meses → 0.5 anos
- `2014` → 14 dias → ~0.038 anos

O cleaner gera a coluna derivada `idade_anos` em anos contínuos, com clipping em [0, 130] (códigos inválidos viram NaN). No SRAG, quando `DT_NASC` existe, ele tem precedência sobre `NU_IDADE_N` (idade mais confiável).

### 4.7. Recode dos códigos 1/2/9

O SINAN/SRAG codificam variáveis binárias como:
- `1` = Sim
- `2` = Não
- `9` = Ignorado

Todos esses campos viram `pandas.BooleanDtype` (`{True, False, NA}`) durante a limpeza. As 22 colunas de sintoma/comorbidade do SINAN clássico estão listadas em `config._SINAN_YES_NO`; as 30 do SRAG em `_SRAG_YES_NO`. Adicionar novas é uma edição no tuple.

### 4.8. IDs IBGE como `string`, não numérico

Códigos IBGE de município (7 dígitos) e UF (2 dígitos) **têm zeros à esquerda significativos** — `33` ≠ `33000` ≠ `033`. Forçar para `int` quebraria a chave. Todos os IDs declarados em `_ID_COLUMNS` (por cleaner) são mantidos como `pandas.StringDtype`.

### 4.9. Leitura em chunks

Os arquivos somam ~2 GB. O `dengue_2025.csv` sozinho tem 458 MB; o `pns2019.csv` tem 922 MB. Carregar tudo em memória estoura facilmente. `io_utils.iter_chunks()` lê em blocos de 100 mil linhas e cada chunk passa pelo `transform_chunk` independentemente.

A consolidação em parquet final ainda materializa o frame inteiro em RAM por uma vez (uso de `pd.concat`). Para os tamanhos atuais isso cabe; se um arquivo crescer 5× substituir por `pyarrow.parquet.ParquetWriter` para escrita streaming.

### 4.10. Strings-sentinela tratadas como NA

CSVs do SUS frequentemente trazem literalmente as strings `"nan"`, `"None"`, `"null"`, `"NaT"`, `"NA"` ou `"-"` no lugar de valores ausentes. O cleaner-base reconhece esse conjunto (`_NA_SENTINELS`) e converte para `pd.NA` no `_strip_strings`. Sem isso, datas viravam string "nan" e jamais eram parseadas (foi exatamente o que aconteceu com `taxa_indic_chikungunya.csv`).

### 4.11. Reprodutibilidade

Toda escolha aleatória usa `RANDOM_SEED = 42` (em `config.py`). Rodando o pipeline duas vezes em sequência sai o mesmo split byte-a-byte.

---

## 5. Como rodar

### 5.0. Pré-requisitos e setup do shell

- Python 3.10+
- `pandas`, `numpy`, `pyarrow`, `pytest` (já em `requirements-ml.txt`)

```powershell
# A partir da raiz do projeto (DATAcare/):
$env:PYTHONPATH = "$PWD\data_pipeline"
cd data_pipeline
```

A pasta dos dados brutos é autodetectada em `..\..\Dados` (relativa à pasta `data_pipeline/`) — ou seja, na pasta `Dados/` ao lado de `DATAcare/`, dentro da raiz do workspace. Para apontar para outro lugar:
```powershell
$env:DATACARE_RAW_DIR = "D:\caminho\diferente"
```

### Visão geral do fluxo

```
        ENTRADA                     ETAPA                       SAÍDA
                              ┌──────────────────┐
                              │                  │
  Dados/*.csv  ──────────────▶│  1. clean.py     │──┬─▶ data_pipeline/data/interim/<dataset>.parquet
  (CSVs brutos, ~2 GB)        │  (Transform)     │  │
                              │                  │  └─▶ data_pipeline/data/reports/cleaning/<dataset>.json
                              └──────────────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │                  │
  data/interim/*.parquet ────▶│  2. split.py     │──┬─▶ data_pipeline/data/processed/train/<dataset>.parquet
                              │  (Partition +    │  ├─▶ data_pipeline/data/processed/val/<dataset>.parquet
                              │   anti-leakage)  │  ├─▶ data_pipeline/data/processed/test/<dataset>.parquet
                              │                  │  │
                              └──────────────────┘  └─▶ data_pipeline/data/reports/leakage/<dataset>.json
```

As duas etapas são independentes e cada uma tem seu CLI. O `run_pipeline.py` é só um atalho que dispara as duas em sequência.

---

### 5.1. Etapa 1 — Limpeza (`clean.py`)

**O que faz:** lê os CSVs brutos em chunks, aplica encoding Latin-1, normaliza strings-sentinela, parseia datas, recodifica códigos 1/2/9 → `boolean`, deriva `idade_anos` (SINAN/SRAG), preserva IDs IBGE como `string`, remove duplicatas exatas e grava parquet único por dataset.

**Lê de:** `Dados\<arquivo>.csv` (resolvido a partir de `..\..\Dados` ou de `$env:DATACARE_RAW_DIR` se setado).

**Grava em:**
| Tipo de saída | Caminho                                                         |
|---------------|-----------------------------------------------------------------|
| Dataset limpo | `data_pipeline\data\interim\<dataset>.parquet`                  |
| Relatório     | `data_pipeline\data\reports\cleaning\<dataset>.json`            |

**Comandos:**
```powershell
# Limpa todos os 8 datasets (~10 min nos dados completos)
python -m src.etl.clean

# Limpa só um (útil para testar)
python -m src.etl.clean --dataset sinan_dengue

# Dry-run: 5 mil linhas por dataset (~30 s)
python -m src.etl.clean --sample 5000

# Lista os dataset slugs aceitos
python -m src.etl.clean --help
```

**O que conferir depois:**
```powershell
ls data\interim                          # deve ter 1 .parquet por dataset
type data\reports\cleaning\sinan_dengue.json   # raw_rows, cleaned_rows, duplicates_dropped
```

---

### 5.2. Etapa 2 — Split (`split.py`)

**O que faz:** lê cada parquet limpo, aplica a estratégia de split declarada no `DatasetSpec` (temporal por `DT_NOTIFIC` / `co_anomes`, ou grouped por `UPA_PNS`), grava três parquets (treino/val/teste) e roda o validador anti-leakage. Se detectar contaminação, o CLI sai com exit code ≠ 0.

**Lê de:** `data_pipeline\data\interim\<dataset>.parquet` (output da etapa 1).

> Se essa pasta estiver vazia, a etapa 2 emite um warning e pula o dataset — rode `clean.py` antes.

**Grava em:**
| Tipo de saída | Caminho                                                              |
|---------------|----------------------------------------------------------------------|
| Treino        | `data_pipeline\data\processed\train\<dataset>.parquet`               |
| Validação     | `data_pipeline\data\processed\val\<dataset>.parquet`                 |
| Teste         | `data_pipeline\data\processed\test\<dataset>.parquet`                |
| Relatório     | `data_pipeline\data\reports\leakage\<dataset>.json`                  |

**Comandos:**
```powershell
# Particiona todos os datasets já limpos (proporção default 0.70 / 0.15 / 0.15)
python -m src.etl.split

# Só um dataset
python -m src.etl.split --dataset sinan_dengue

# Proporções customizadas — devem somar 1.0
python -m src.etl.split --train 0.8 --val 0.1 --test 0.1

# Combinando
python -m src.etl.split --dataset pns_2019 --train 0.6 --val 0.2 --test 0.2
```

**O que conferir depois:**
```powershell
ls data\processed\train, data\processed\val, data\processed\test
type data\reports\leakage\sinan_dengue.json        # errors deve ser []
```

Detalhes do validador estão na §4.3.

---

### 5.3. Atalho — pipeline completo (`run_pipeline.py`)

Dispara as duas etapas em sequência. Equivale a `clean.py` seguido de `split.py` com os mesmos argumentos.

```powershell
# Tudo, dados completos
python -m src.etl.run_pipeline

# Tudo, dry-run rápido
python -m src.etl.run_pipeline --sample 5000

# Um dataset, do bruto até o particionado
python -m src.etl.run_pipeline --dataset sinan_dengue

# Customizando proporções no atalho também
python -m src.etl.run_pipeline --train 0.8 --val 0.1 --test 0.1 --sample 5000
```

**Recomendação:** use `run_pipeline.py` no dia a dia. Os CLIs separados (`clean.py` / `split.py`) servem para reprocessar uma etapa só — por exemplo: mudou a estratégia de split e quer rerodar apenas o particionamento sem repagar o custo da limpeza dos 2 GB.

---

### 5.4. Testes

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest tests/etl
```

> O `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` contorna uma instalação quebrada de Hydra/omegaconf no Python global. Em venv isolado não é necessário.

Esperado: `31 passed` em ~0,5 s. Não toca em dados reais — todos os testes usam DataFrames sintéticos.

---

### 5.5. Tabela-resumo de onde cada coisa pára

| Após…                  | Você encontra em…                                | Formato       |
|------------------------|--------------------------------------------------|---------------|
| `clean.py`             | `data_pipeline\data\interim\`                    | Parquet       |
| `clean.py`             | `data_pipeline\data\reports\cleaning\`           | JSON          |
| `split.py`             | `data_pipeline\data\processed\train\`            | Parquet       |
| `split.py`             | `data_pipeline\data\processed\val\`              | Parquet       |
| `split.py`             | `data_pipeline\data\processed\test\`             | Parquet       |
| `split.py`             | `data_pipeline\data\reports\leakage\`            | JSON          |
| `run_pipeline.py`      | tudo acima (executa as duas etapas em sequência) | Parquet + JSON|

---

## 6. Como verificar que funcionou

### Nível 1: pytest verde
```powershell
python -m pytest tests/etl
# espera: 31 passed
```

### Nível 2: relatórios sem `errors`
Após rodar o pipeline, inspecione qualquer `data/reports/leakage/<dataset>.json`:
```json
{
  "errors": [],            ← TEM QUE SER LISTA VAZIA
  "warnings": [],          ← warnings são toleráveis
  "duplicate_rows_across_splits": 0,
  "group_overlaps": {"train_x_val": 0, "train_x_test": 0, "val_x_test": 0},
  "temporal_order_ok": true
}
```

### Nível 3: tipos corretos no parquet
```powershell
python -c "import pandas as pd; df = pd.read_parquet('data/processed/train/sinan_dengue.parquet'); print(df.dtypes.value_counts())"
```
Espere ver `boolean`, `datetime64[ns]`, `string[python]`, `float64` — não só `object`.

### Nível 4: prova visual de que o split temporal é estrito
```powershell
python -c "import pandas as pd; [print(s, '->', pd.read_parquet(f'data/processed/{s}/sinan_dengue.parquet')['DT_NOTIFIC'].agg(['min','max']).to_dict()) for s in ['train','val','test']]"
```
Resultado esperado: `max(train) < min(val) < min(test)`. Se vir intervalos sobrepostos, há leakage.

### Nível 5: Data Wrangler ou Tad Viewer
Abre `data/processed/train/sinan_dengue.parquet` no Data Wrangler (VS Code, botão direito → Open in Data Wrangler) ou no Tad. Confirma visualmente que `FEBRE` virou `bool`, `DT_NOTIFIC` virou data, `idade_anos` está em anos coerentes, etc.

---

## 7. Bugs corrigidos durante o desenvolvimento

Notas curtas sobre erros encontrados e a causa-raiz — útil se algo parecido reaparecer.

### 7.1. Path resolution incorreto
**Sintoma:** `FileNotFoundError: Arquivo bruto não encontrado` apontando para um diretório acima do esperado (faltava um nível na hierarquia).
**Causa:** `PROJECT_ROOT.parent.parent` subia dois níveis em vez de um. O nome `PROJECT_ROOT` na verdade já era `.../DATAcare`, não `.../DATAcare/data_pipeline`.
**Fix:** renomeei para `PIPELINE_ROOT`, `DATACARE_ROOT`, `WORKSPACE_ROOT` deixando a hierarquia explícita.

### 7.2. `fillna("__NA__")` em colunas `boolean`
**Sintoma:** `TypeError: Invalid value '__NA__' for dtype 'boolean'` ao validar leakage do SRAG.
**Causa:** o validador chamava `df.fillna("__NA__")` antes de hashear, mas a dtype nullable boolean do pandas rejeita string como valor de preenchimento.
**Fix:** removi o `fillna`. `pd.util.hash_pandas_object` já trata NaN consistentemente em qualquer dtype.

### 7.3. `FutureWarning` em `replace({"": pd.NA})`
**Sintoma:** warning de "Downcasting behavior in `replace` is deprecated" em todo cleaner.
**Causa:** pandas 2.3 mudou o comportamento de downcast após `replace` por NA.
**Fix:** troquei por `mask(is_sentinel, pd.NA)`. De brinde, ampliei o tratamento para reconhecer também `"nan"`, `"none"`, `"null"`, `"nat"`, `"-"` como NA — *exatamente* o problema que causou o bug 7.5.

### 7.4. `dayfirst=True` em ISO timestamp
**Sintoma:** `UserWarning: Parsing dates in %Y-%m-%d %H:%M:%S format when dayfirst=True was specified.`
**Causa:** chamei `to_datetime(dayfirst=True)` em `dt_atualizacao`, que é timestamp do sistema (sempre ISO), não data preenchida por humano (`DD/MM/AAAA`).
**Fix:** removi `dayfirst` desse parse específico. Mantive para `dt_competencia` que é manual.

### 7.5. `taxa_indic_chikungunya.csv` sem dado temporal
**Sintoma:** `ValueError: Coluna 'co_anomes' sem valores válidos — split temporal impossível.`
**Causa-raiz:** o arquivo bruto traz literalmente a string `"nan"` em todas as 5000 linhas de `co_anomes`, e `"None"` em `dt_competencia`. A fonte (provavelmente um Tabnet do DataSUS) dropou a competência temporal antes de exportar. Os outros dois `taxa_incid_*` vêm completos.
**Fix:** adicionei o campo `fallback_group_column` em `DatasetSpec`. Quando o splitter detecta que o time column está 100% NA e há fallback declarado, cai para `GroupedSplitter` na coluna fallback (`co_ibge` = município). Loga um WARNING explícito para deixar visível. Anti-leakage geográfico fica preservado mesmo sem o eixo temporal.

---

## 8. Limitações conhecidas / dados problemáticos

### 8.1. `taxa_incid_chikungunya` sem tempo
A fonte publica esse arquivo sem `co_anomes` nem `dt_competencia`. O split caiu para grouped por `co_ibge`. **Implicação para ML:** esse dataset não pode contribuir para feature engineering temporal (sazonalidade, defasagens) — só para agregados estáticos por município. Vale baixar novamente do DataSUS num momento futuro para confirmar se a fonte corrigiu.

### 8.2. SINAN sem identificador de paciente
Os arquivos do SINAN não trazem um ID de paciente real (apenas `NU_NOTIFIC` da notificação). Não dá para checar se um mesmo paciente apareceu em múltiplas notificações dentro do mesmo dataset. **Implicação:** o split temporal protege contra contaminação cronológica, mas se duas notificações do mesmo paciente caírem em splits diferentes, o validador não detecta — porque eles parecem registros independentes. Mitigação parcial: o cleaner remove duplicatas *exatas* (mesma combinação de todas as colunas), e o índice composto `(ANO_NASC, CS_SEXO, ID_MUNICIP)` poderia ser usado como proxy futuro se for relevante.

### 8.3. Proporções de grouped split não batem exatamente em 70/15/15
Splits por grupo (PNS, e o fallback de chikungunya) embalam todas as linhas de um mesmo grupo no mesmo split, e os grupos têm tamanhos variáveis (UPAs com 5–15 respondentes, municípios com contagens diferentes). Resultado real do smoke-test do PNS: `0.69 / 0.15 / 0.17` em vez de exato `0.70 / 0.15 / 0.15`. O validador aceita esse desvio com `ratio_tolerance=0.05` (5 p.p.). **Não dá pra reduzir mais sem permitir leakage**; é o preço da garantia de cluster intacto.

### 8.4. 76 colunas do SINAN dengue ainda como `object`
O cleaner só tipou explicitamente: 22 booleans, 7 datas, 16 IDs como string e 1 float (`idade_anos`). As outras 76 colunas ficaram como `object` (string genérica). Não é lixo — só significa que ninguém decidiu ainda se devem ser categóricas, numéricas ou texto livre. Essa decisão é da próxima etapa (feature engineering / HU-05).

### 8.5. Cleaning report não conta linhas filtradas por chunk
O relatório agrega o total `raw_rows` (entrada) e `cleaned_rows` (saída) mas não distingue *por qual motivo* uma linha sumiu (duplicata, todos nulos, linha mal formada lida com `on_bad_lines="warn"`). `duplicates_dropped` é a única categoria contada. Suficiente por enquanto; pode ser refinado se a auditoria pedir.

---

## 9. Próximos passos

Esta branch *não* faz:

- **HU-04 EDA**: análise descritiva pós-split, lendo só `processed/train/`. Vai num notebook em `data_pipeline/notebooks/` ou pasta equivalente.
- **HU-05 Feature engineering**: criar variáveis derivadas (`tem_sintoma_respiratorio`, `num_comorbidades`, faixa etária, encoding de UF, etc.) e gravar em `data/features/`.
- **HU-06 Modelo**: treina lendo *apenas* `train/`, valida em `val/`, e reporta em `test/` **uma vez só** ao final. O contrato de splits dessa branch garante que essa hierarquia faz sentido.
- **HU-02 Banco de dados**: carga dos parquets para o Postgres. Diferente desta branch porque envolve schema, migrations, normalização — escolha de design separada.

A regra para o consumidor dessa branch é simples: **tudo o que for treinar ou validar lê de `data_pipeline/data/processed/<split>/`. Nunca direto do `Dados/` bruto.**

---

## 10. Apêndice: glossário rápido

| Sigla / termo | Significado                                                                 |
|---------------|------------------------------------------------------------------------------|
| **SINAN**     | Sistema de Informação de Agravos de Notificação (SUS, doenças notificáveis). |
| **SRAG**      | Síndrome Respiratória Aguda Grave; arquivo `influeza_srag` é do SIVEP-Gripe.  |
| **PNS**       | Pesquisa Nacional de Saúde (IBGE+MS, microdados domiciliares).                |
| **UPA_PNS**   | Unidade Primária de Amostragem da PNS (cluster do desenho amostral).          |
| **UPA (rede)**| Unidade de Pronto Atendimento (SUS) — **NÃO** é a mesma coisa que UPA_PNS.    |
| **APS**       | Atenção Primária à Saúde.                                                     |
| **ACS**       | Agente Comunitário de Saúde.                                                  |
| **co_ibge**   | Código IBGE do município (7 dígitos).                                         |
| **co_anomes** | Competência no formato AAAAMM (ex.: `202401` = janeiro/2024).                 |
| **CLASSI_FIN**| Classificação final do caso (códigos variam por agravo).                     |
| **EVOLUCAO**  | Desfecho do caso (cura/óbito/etc.).                                          |
| **dictionary encoding** | Compressão de Parquet que armazena valores repetidos uma única vez. |
| **leakage**   | Vazamento de informação entre treino e teste, inflacionando métricas.        |
| **dry-run**   | Execução de amostra (`--sample N`) para validar sem rodar nas ~2 GB inteiras.|

---

**Dúvidas, ou alguma decisão acima que queira revisar?** Abra uma issue ou edite este arquivo na próxima branch — ele é o oráculo do que ficou definido em `feature/data-cleaning-split`.
