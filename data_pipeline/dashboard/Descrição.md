# DATAcare — Dashboard de ML & ETL (Streamlit)

Dashboard interativo (paleta branco + verde) que documenta, ponta a ponta, o
pipeline de dados e os modelos de Machine Learning do DATAcare. Toda a interface
é construída em `app.py` (UI, gráficos Plotly e CSS) apoiada em `data_access.py`
(leitura tolerante a falhas dos artefatos do pipeline).

- **Arquivo principal:** `data_pipeline/dashboard/app.py`
- **Acesso a dados:** `data_pipeline/dashboard/data_access.py`
- **Tema Streamlit:** `data_pipeline/dashboard/.streamlit/config.toml`
- **URL padrão:** http://localhost:8501

---

## Visão geral da interface

- **Layout** em modo *wide*, com barra lateral expandida e largura máxima de
  conteúdo de ~1400 px.
- **Identidade visual própria:** um bloco de CSS extenso esconde os elementos
  nativos do Streamlit (barra superior, menu, botão *Deploy*, rodapé "Made with
  Streamlit") e aplica a paleta verde a métricas, tabelas, inputs, abas, botões
  e alertas — funcionando tanto no tema claro quanto no escuro.
- **Gráficos sem distrações:** todos os Plotly são renderizados pelo helper
  `chart()`, que remove a *toolbar* (zoom, pan, salvar, fullscreen), desativa
  scroll/duplo-clique/seleção e mantém apenas um *tooltip* estilizado. Eixos têm
  `fixedrange` (sem arrasto/zoom).
- **Paleta:** escala de verdes (`GREEN_50` → `GREEN_900`) com cores fixas por
  doença (dengue, chikungunya, zika, influenza) e por severidade (baixo = verde,
  médio = âmbar, alto = vermelho); heatmaps e barras de importância usam a escala
  contínua `GREEN_SCALE`.
- **Componentes visuais reutilizáveis:** *hero* (cabeçalho em gradiente verde),
  `kpi_hero` (cards de KPI), `callout` (destaques verdes com número grande),
  `gauge` (medidor radial 0–100%), `confusion_heatmap` (matriz de confusão),
  `proba_bar` (barras horizontais de probabilidade) e pílulas de status
  (`status_pill`: ✓ OK / ! Falha).

## Barra lateral (sidebar)

- **Marca** "🩺 DATAcare — ML & ETL · Saúde Digital para APS".
- **Navegação** por *radio* entre as 7 páginas (ver abaixo).
- **Botão "Atualizar dados"**: limpa o cache (`st.cache_data.clear()`) e recarrega
  os relatórios. O cache também é invalidado automaticamente quando os arquivos
  de relatório mudam (via assinaturas de `mtime`).

---

## Páginas

| # | Página | Função | Conteúdo principal |
|---|--------|--------|--------------------|
| 1 | **Visão Geral** | `page_overview` | KPIs e gauges dos modelos, destaques, comparação de algoritmos, distribuição de classes e resumo do ETL |
| 2 | **ETL & Qualidade de Dados** | `page_etl` | Abas de Limpeza, Split e Vazamento |
| 3 | **Comparação de Modelos** | `page_comparison` | RF × Árvore de Decisão (métrica selecionável, tabela e modelo escolhido) |
| 4 | **Previsões ao Vivo** | `page_predict` | Formulário clínico + inferência dos dois modelos |
| 5 | **Classificador de Doença** | `page_disease` | Detalhe do modelo de doença |
| 6 | **Classificador de Severidade** | `page_severity` | Detalhe do modelo de severidade |
| 7 | **Exploração de Dados** | `page_explore` | Distribuições dos parquets limpos |

> A ordem na barra lateral é: Visão Geral · ETL & Qualidade de Dados ·
> Comparação de Modelos · Previsões ao Vivo · Classificador de Doença ·
> Classificador de Severidade · Exploração de Dados.

---

### 1. Visão Geral (`page_overview`)

Painel-resumo de todo o pipeline. Elementos, de cima para baixo:

- **Hero** "Visão geral do pipeline DATAcare" com *tags* dinâmicas: acurácia de
  doença, acurácia de severidade, número de datasets ativos e
  "0 vazamentos entre splits".
- **4 KPIs** (cards `kpi_hero`): Acurácia · Doença (com Macro-F1), Acurácia ·
  Severidade (com Macro-F1), CV F1 · Doença (± desvio) e CV F1 · Severidade
  (± desvio).
- **4 gauges** (medidores radiais), exibidos quando ambos os modelos existem:
  Acurácia · Doença, Macro-F1 · Doença, Acurácia · Severidade e CV F1 ·
  Severidade.
- **Destaques do modelo** — até 4 `callout`: as 2 classes de doença com maior
  F1, a acurácia de severidade e a estabilidade da validação cruzada (desvio
  entre folds).
- **Comparação de algoritmos (Macro-F1)** — gráfico de **barras agrupadas**
  (Random Forest × Árvore de Decisão) por tarefa.
- **Distribuição de classes · Doença** — gráfico de **rosca (donut)** com o
  suporte (nº de amostras) por classe no conjunto de teste.
- **Resumo do ETL** — 4 `st.metric`: Datasets processados, Linhas brutas, Linhas
  limpas e Retenção média (com *delta* de duplicatas removidas).
- **Rodapé** descrevendo o fluxo: CSVs brutos → ETL local → ml-trainer → backend.

### 2. ETL & Qualidade de Dados (`page_etl`)

Organizada em **3 abas**. Se não houver relatórios de ETL, exibe um aviso
orientando a rodar `python -m src.etl.run_pipeline`.

- **🧹 Limpeza**
  - 3 métricas: Linhas brutas, Linhas após limpeza, Retenção média.
  - **Barras empilhadas** "Linhas brutas × limpas por dataset" (mantidas em
    verde × removidas em vermelho).
  - **Barras horizontais** "Retenção de dados após limpeza" (% por dataset,
    escala de cor verde contínua).
  - Duas colunas lado a lado: **barras** de "Duplicatas removidas" e de
    "Colunas recodificadas (sim/não/ignorado)".
  - **Tabela "Detalhamento"** por dataset (arquivo de origem, brutas, limpas,
    retenção %, duplicatas, datas inválidas, colunas recodificadas, colunas de
    data).
- **✂️ Split**
  - **Barras empilhadas** "Tamanho dos splits (train / val / test)" em linhas.
  - **Barras agrupadas** "Proporção dos splits (%)" por dataset.
- **🛡️ Vazamento**
  - 3 métricas: Splits com ordem temporal OK (x/total), Linhas duplicadas entre
    splits, Sobreposições de grupo.
  - `callout` "Zero vazamento entre splits" quando duplicatas e sobreposições
    são zero.
  - **Status por dataset**: para cada dataset, pílulas de status (✓/!) de Ordem
    temporal, Sem duplicatas, Sem overlap e veredito Geral (Aprovado/Revisar),
    além da estratégia de split usada.

### 3. Comparação de Modelos (`page_comparison`)

Compara **Random Forest × Árvore de Decisão** nas duas tarefas. Mostra aviso se
não houver relatórios de ML.

- **Selectbox "Métrica em destaque"**: Macro-F1, Acurácia ou CV F1 (média).
- **Barras agrupadas** da métrica escolhida, por tarefa e algoritmo.
- **Tabela comparativa** com Acurácia, Macro-F1, CV F1 (média) e marcação
  ✅ do algoritmo selecionado em cada tarefa.
- **Cards "Modelo selecionado por tarefa"** (um por tarefa) com o algoritmo
  vencedor, pílula "selecionado" e CV F1 ± desvio.

### 4. Previsões ao Vivo (`page_predict`)

Formulário clínico que aciona os dois classificadores em tempo real.

- **Status dos modelos**: pílula verde "Modelos prontos…" quando os artefatos
  MLflow existem, ou faixa âmbar "Modelos indisponíveis — exibindo cenário
  didático" quando não.
- **Dados do paciente**: *slider* de Idade (0–100), *radio* de Sexo, *slider* de
  Mês da notificação (1–12) e Semana epidemiológica (1–53), *selectbox* de UF
  (10 UFs com código IBGE) e *number input* de Município (código IBGE).
- **Quadro clínico** em 4 abas de *checkboxes*: Sintomas (arboviroses, 14 itens
  do SINAN), Sintomas respiratórios (6 itens do SRAG), Comorbidades (12 itens) e
  Contexto (Hospitalização).
- **Botão "Rodar predição"**: monta o vetor de features e chama
  `predict_full_safe`. Sem artefatos MLflow, cai para um **cenário didático**
  (predição de demonstração de dengue).
- **Resultado** em 2 colunas: cards de "Doença prevista" e "Severidade prevista"
  (classe + confiança) e, abaixo de cada um, **barras horizontais** de
  probabilidade por classe (`proba_bar`).
- **"Sinais clínicos relevantes"**: cruza os sintomas marcados com a importância
  de features do modelo de doença e plota **barras horizontais** dos sinais que
  têm peso no modelo.

### 5. Classificador de Doença (`page_disease`)

Usa o detalhe genérico `render_model_detail` com o relatório do
`disease_classifier` (dengue × chikungunya × zika × influenza). Elementos:

- **4 KPIs** (`kpi_hero`): Acurácia (sobre nº de amostras de teste), Macro-F1,
  CV F1 (média ± desvio) e Algoritmo selecionado.
- **3 gauges**: Acurácia, Macro-F1 e CV F1.
- **Destaques de classes**: até 3 `callout` com as classes de maior F1.
- **Matriz de confusão** (heatmap verde) com **toggle "Normalizar por linha
  (recall)"** (contagem absoluta × proporção).
- **Barras horizontais** "F1-score por classe".
- **Barras agrupadas** "Precisão × Recall por classe".

### 6. Classificador de Severidade (`page_severity`)

Idêntica em estrutura à página de doença (mesmo `render_model_detail`), porém
para o `severity_classifier` com as classes **baixo × médio × alto**. Apresenta
os mesmos elementos: 4 KPIs, 3 gauges, destaques de classes, matriz de confusão
com toggle de normalização, F1 por classe e Precisão × Recall por classe.

### 7. Exploração de Dados (`page_explore`)

Calcula distribuições diretamente sobre os parquets limpos (somente os 4
datasets ativos). Exibe aviso se nenhum parquet for encontrado.

- **Selectbox "Dataset"** com rótulos amigáveis (ex.: "Dengue (SINAN)").
- **3 métricas**: Linhas, Colunas e tamanho da amostra usada nos gráficos
  (até 150.000 linhas).
- **3 abas**:
  - **📊 Distribuições**: **histograma** de Idade, **rosca** de Sexo e **barras**
    da distribuição da coluna de classificação (`CLASSI_FIN`).
  - **🦠 Sintomas**: **multiselect** de variáveis booleanas (sintomas/
    comorbidades) e **barras horizontais** de prevalência (%) de cada uma.
  - **🗓️ Temporal**: **gráfico de área** das notificações por mês (a partir da
    coluna de data detectada).

> A detecção de colunas (idade, data, sexo, classe) é semântica e robusta entre
> os esquemas SINAN e SRAG (ver `detect_*` em `data_access.py`).

---

## Fontes de dados

Tudo é lido dos artefatos gerados pelo pipeline (não há banco de dados). O
`data_access.py` é tolerante a falhas: se um artefato não existe, a página
mostra um aviso (`empty_state`) em vez de quebrar.

- `data_pipeline/data/reports/cleaning/*.json` — relatórios de limpeza
- `data_pipeline/data/reports/leakage/*.json` — split + vazamento
- `data_pipeline/data/reports/ml/disease_classifier_report.json` — métricas do modelo de doença
- `data_pipeline/data/reports/ml/severity_classifier_report.json` — métricas do modelo de severidade
- `data_pipeline/data/interim/*.parquet` — dados limpos (página de exploração)
- `data_pipeline/models/<task>/` — artefatos MLflow (previsão ao vivo)

> **Allowlist de datasets:** apenas os 4 datasets ativos (`sinan_dengue`,
> `sinan_chikungunya`, `sinan_zika`, `srag_influenza`) são expostos. Parquets/
> relatórios órfãos de rodadas antigas (ex.: `pns_2019`, `taxa_incid_*`) são
> silenciosamente ignorados. A fonte da verdade é `src.etl.config.DATASETS`.

---

## Rodar via Docker (recomendado)

Sobe junto com toda a stack:

```bash
docker compose up -d
# Dashboard: http://localhost:8501
```

Ou apenas o dashboard (lê os relatórios/parquets que já existirem no volume;
gere-os antes com o ETL local e o treino):

```bash
docker compose up -d dashboard
```

No Docker, o dashboard reusa a imagem de ML (`datacare-ml:local`), que já traz
as dependências — por isso não precisa de Dockerfile/imagem próprios.

## Rodar localmente

As dependências do dashboard (`streamlit`, `plotly`, `pandas`, `pyarrow`) já
fazem parte do `requirements.txt` do projeto — não há mais um requirements
separado. Para um ambiente só do dashboard, basta:

```bash
pip install streamlit plotly pandas pyarrow   # ou: pip install -r requirements.txt
streamlit run data_pipeline/dashboard/app.py
# http://localhost:8501
```

## Atualizar após novo treino/ETL

Use o botão **Atualizar dados** na barra lateral (limpa o cache e relê os
relatórios). O cache também é invalidado automaticamente quando os arquivos de
relatório mudam.
