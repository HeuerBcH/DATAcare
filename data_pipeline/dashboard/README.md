# DATAcare — Dashboard de ML & ETL (Streamlit)

Dashboard interativo que documenta o pipeline de dados e os modelos do DATAcare.

## Páginas

| Página | Conteúdo |
|--------|----------|
| **Visão Geral** | KPIs dos modelos (acurácia/F1) e do ETL (linhas, duplicatas) |
| **ETL & Qualidade de Dados** | Limpeza (brutas × limpas, duplicatas), split (train/val/test) e checagem de vazamento |
| **Comparação de Modelos** | Random Forest × Árvore de Decisão (acurácia, macro-F1, CV) |
| **Classificador de Doença** | Matriz de confusão, métricas por classe, importância de features |
| **Classificador de Severidade** | Idem, para baixo/médio/alto |
| **Exploração de Dados** | Distribuições (idade, sexo, sintomas, série temporal) dos parquets limpos |

## Fontes de dados

Tudo é lido dos artefatos gerados pelo pipeline (não há banco de dados):

- `data_pipeline/data/reports/cleaning/*.json` — relatórios de limpeza
- `data_pipeline/data/reports/leakage/*.json` — split + vazamento
- `data_pipeline/data/reports/ml/*_report.json` — métricas dos modelos
- `data_pipeline/data/interim/*.parquet` — dados limpos (exploração)

Se algum artefato ainda não existe, a página mostra um aviso em vez de quebrar.

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

## Rodar localmente

As dependências do dashboard (`streamlit`, `plotly`, `pandas`, `pyarrow`) já
fazem parte do `requirements.txt` do projeto — não há mais um requirements
separado. Para um ambiente só do dashboard, basta:

```bash
pip install streamlit plotly pandas pyarrow   # ou: pip install -r requirements.txt
streamlit run data_pipeline/dashboard/app.py
# http://localhost:8501
```

No Docker, o dashboard reusa a imagem de ML (`datacare-ml:local`), que já traz
essas dependências — por isso não precisa de Dockerfile/imagem próprios.

## Atualizar após novo treino/ETL

Use o botão **🔄 Atualizar dados** na barra lateral (limpa o cache e relê os
relatórios). O cache também é invalidado automaticamente quando os arquivos
de relatório mudam.
