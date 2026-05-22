# `data_pipeline` — ETL e particionamento dos dados públicos do SUS

Pipeline reprodutível que faz **limpeza** e **separação em treino/validação/teste** dos arquivos brutos em `Dados/`, com checagem de **vazamento** entre subconjuntos antes de qualquer treino de modelo.

> Branch atual: `feature/data-cleaning-split` (derivada de `feature/data-etl`).

---

## Fontes de dados tratadas

| Dataset (slug)            | Arquivo bruto                  | Família       | Tamanho |
|---------------------------|--------------------------------|---------------|---------|
| `sinan_chikungunya`       | `chikungunya_2025.csv`         | SINAN caso    | ~70 MB  |
| `sinan_dengue`            | `dengue_2025.csv`              | SINAN caso    | ~458 MB |
| `sinan_zika`              | `zika_2025.csv`                | SINAN caso    | ~4 MB   |
| `srag_influenza`          | `influeza_srag_2025.csv`       | SRAG (SIVEP)  | ~382 MB |
| `pns_2019`                | `pns2019.csv`                  | PNS microdados| ~922 MB |
| `taxa_incid_dengue`       | `taxa_incid_dengue.csv`        | Taxa agregada | ~145 MB |
| `taxa_incid_zika`         | `taxa_incid_zika.csv`          | Taxa agregada | ~30 MB  |
| `taxa_incid_chikungunya`  | `taxa_indic_chikungunya.csv`   | Taxa agregada | ~73 MB  |

Arquivos `sinannet_*_2025.csv` (1–3 KB) são cabeçalhos de relatório TabWin sem dados — ignorados. PDFs/XLS de dicionário ficam como referência, fora do ETL.

---

## Como rodar

A pasta dos dados brutos é descoberta automaticamente em `..\..\Dados` em relação a este `README` — ou seja, ao lado da pasta `DATAcare/`, na raiz do workspace. Para apontar para outro lugar:

```powershell
$env:DATACARE_RAW_DIR = "D:\caminho\diferente"
```

Da raiz do projeto (`DATAcare/`):

```powershell
$env:PYTHONPATH = "$PWD\data_pipeline"
```

### Pipeline completo (todos os datasets)

```powershell
python -m src.etl.run_pipeline
```

### Modo dry-run (5 mil linhas por dataset, ~1 min)

```powershell
python -m src.etl.run_pipeline --sample 5000
```

### Só um dataset

```powershell
python -m src.etl.run_pipeline --dataset sinan_dengue
```

### Etapas isoladas

```powershell
python -m src.etl.clean --dataset sinan_dengue --sample 5000
python -m src.etl.split --dataset sinan_dengue --train 0.7 --val 0.15 --test 0.15
```

### Testes

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest data_pipeline/tests/etl
```

> O `PYTEST_DISABLE_PLUGIN_AUTOLOAD` contorna uma instalação de Hydra/omegaconf quebrada no Python global. Em venv isolado não é necessário.

---

## Arquitetura

```
data_pipeline/
├── src/
│   ├── etl/
│   │   ├── config.py              # caminhos + DatasetSpec por fonte
│   │   ├── io_utils.py            # leitura em chunks + escrita parquet
│   │   ├── cleaners/
│   │   │   ├── base.py            # parsing de datas, recode 1/2/9, dedup
│   │   │   ├── sinan.py           # NU_IDADE_N composto, CS_SEXO, IDs IBGE
│   │   │   ├── srag.py            # DT_NASC > NU_IDADE_N fallback
│   │   │   ├── pns.py             # preserva UPA_PNS / V0001 / pesos
│   │   │   └── taxa_incid.py      # numéricos + competência
│   │   ├── splitters/
│   │   │   ├── strategies.py      # Temporal / Grouped / StratifiedTemporal
│   │   │   └── leakage.py         # validador anti-contaminação
│   │   ├── clean.py               # CLI: limpa N datasets → interim/
│   │   ├── split.py               # CLI: lê interim/ → processed/{train,val,test}/
│   │   └── run_pipeline.py        # CLI: clean + split em uma chamada
│   └── utils/logging_config.py
├── data/
│   ├── interim/                   # parquet limpo (uma por dataset)
│   ├── processed/{train,val,test}/  # parquet particionado
│   └── reports/{cleaning,leakage}/  # relatórios JSON
└── tests/etl/
    ├── test_cleaners.py
    └── test_splitters.py
```

---

## Estratégia anti-contaminação por dataset

A escolha do tipo de split depende da **unidade de observação** e do que o modelo precisa generalizar.

| Dataset                | Estratégia       | Coluna decisiva  | Por quê                                                                                                              |
|------------------------|------------------|------------------|----------------------------------------------------------------------------------------------------------------------|
| SINAN dengue/chik/zika | **temporal**     | `DT_NOTIFIC`     | Em deployment, o modelo só vê notificações *futuras*. Dividir aleatoriamente vazaria padrões sazonais.               |
| SRAG/Influenza         | **temporal**     | `DT_NOTIFIC`     | Mesmo motivo do SINAN — surveillance é uma série temporal.                                                            |
| PNS 2019               | **grouped**      | `UPA_PNS`        | PNS é survey clusterizado: pessoas da mesma UPA são correlacionadas. Quebrar uma UPA entre splits = leakage por cluster. |
| Taxa de incidência     | **temporal**     | `co_anomes`      | Mesmo município repete a cada mês — split aleatório vazaria autocorrelação espaço-temporal.                          |

> **Fallback:** datasets de taxa de incidência declaram `fallback_group_column="co_ibge"`. Se `co_anomes` chegar inteiro inválido (caso real: `taxa_indic_chikungunya.csv` traz o campo como string `"nan"` da fonte), o pipeline cai para **grouped split por município** e loga um WARNING. Anti-leakage geográfico fica preservado mesmo sem o eixo temporal.

### O que o validador checa (`splitters/leakage.py`)

Roda automaticamente após cada split e grava `reports/leakage/<dataset>.json`:

1. **`duplicate_rows_across_splits`** — nenhuma linha (hash de todas as colunas) aparece em mais de um split.
2. **`group_overlaps`** — para splits por grupo, nenhuma chave de grupo (UPA, paciente etc.) é compartilhada.
3. **`temporal_order_ok`** — para splits temporais, `max(train) < min(val) < min(test)`.
4. **`ratios`** dentro da tolerância de 5 p.p.

Se algum dos três primeiros falhar, o split é considerado contaminado e o exit code do CLI é 1.

---

## O que a limpeza faz (resumo)

- **Encoding**: Latin-1 forçado em todos os CSVs do SUS (mojibake confirmado).
- **Strings**: `strip()` + `""` → `NA`.
- **Datas**: tenta formato ISO e fallback `dayfirst=True` (DD/MM/AAAA).
- **`NU_IDADE_N`** (SINAN/SRAG): decodifica o formato composto onde o primeiro dígito indica unidade (`1=hora, 2=dia, 3=mês, 4=ano`) e os 3 últimos o valor — gera coluna derivada `idade_anos` em anos.
- **`CS_SEXO`**: normaliza para `{M, F, I}`; outros → `NA`.
- **Códigos 1/Sim, 2/Não, 9/Ignorado**: viram `pandas.BooleanDtype` ({True, False, NA}).
- **IDs IBGE** (`ID_MUNICIP`, `co_ibge`, `UPA_PNS`, etc.): mantidos como `string` para preservar zeros à esquerda.
- **Duplicatas exatas**: removidas e contadas.
- **Saída**: Parquet (até ~8× menor que CSV, com tipos).

Todo o resumo do que aconteceu vira `reports/cleaning/<dataset>.json`:

```json
{
  "dataset": "sinan_zika",
  "raw_rows": 5000,
  "cleaned_rows": 4995,
  "duplicates_dropped": 5,
  "yes_no_columns_recoded": ["FEBRE", "MIALGIA", ...],
  "date_columns_parsed": ["DT_NOTIFIC", "DT_SIN_PRI", ...]
}
```

---

## Reprodutibilidade

- Toda escolha aleatória usa `RANDOM_SEED = 42` (definido em `config.py`).
- Datasets, separadores, encoding e estratégia de split vivem em `DATASETS` do `config.py` — adicionar uma nova fonte é uma única entrada nesse dicionário.

---

## Próximos passos (fora desta entrega)

1. EDA pós-split (em `notebooks/`), só lendo `processed/train/`.
2. Feature engineering por dataset → escreve em `data/features/`.
3. Modelo: treina lendo apenas `train/`, valida em `val/`, reporta em `test/` **uma vez só** ao final.
