# syntax=docker/dockerfile:1
# ============================================================================
# DATAcare — Dockerfile unificado (multi-stage, multi-target).
#
# Um único arquivo com 2 alvos de build; o docker-compose escolhe qual construir
# via `target:`. O frontend (Node/Vite) vive no Dockerfile.frontend (outro runtime).
#
#   target: backend  -> Django + Gunicorn          (Python 3.12, multi-stage)
#   target: ml       -> MLflow server + treino ML + dashboard Streamlit (Python 3.11)
#
# O alvo `ml` serve três serviços (mlflow, ml-trainer, dashboard) — só muda o
# comando no compose; por isso a imagem traz streamlit/plotly no requirements.
#
# Build manual de um alvo específico:
#   docker build --target ml -t datacare-ml:local .
# ============================================================================

# ---------------------------------------------------------------------------
# Backend (Django) — multi-stage: o builder compila as deps, o runtime fica enxuto.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS backend-builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


FROM python:3.12-slim AS backend

WORKDIR /app

# Dependências apenas de runtime.
# curl é necessário para o healthcheck do compose (curl -f http://localhost:8000/admin/);
# sem ele o container fica eternamente "unhealthy".
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pacotes Python vindos do builder.
COPY --from=backend-builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY . .

RUN mkdir -p logs static staticfiles media
RUN python backend/manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "config.wsgi:application"]


# ---------------------------------------------------------------------------
# ML — serve TRÊS serviços do compose (mesma imagem, comandos diferentes):
#   1) mlflow      -> servidor de tracking + UI (mlflow server)
#   2) ml-trainer  -> treino/comparação dos modelos (python -m src.models.train)
#   3) dashboard   -> Streamlit (a imagem já traz streamlit/plotly via requirements)
# Python 3.11: o CLI do MLflow 2.10 (`mlflow server`) é incompatível com 3.12+
# (importlib.metadata.entry_points().get() foi removido); 3.11 mantém o MLflow
# 2.10 e os modelos já salvos. O ETL roda FORA do Docker — veja data_pipeline/README.md.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS ml

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# build-essential: compila pacotes científicos no pip install. curl: healthchecks.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependências primeiro (melhor cache de camadas).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código do projeto (data_pipeline e dados reais são montados via volume no
# compose; o COPY garante que a imagem funcione mesmo sem bind mount).
COPY . .

# O código de ML é importado como pacote `src.*` a partir de data_pipeline/.
# GIT_PYTHON_REFRESH=quiet silencia o aviso do MLflow quando não há git no PATH.
ENV PYTHONPATH=/app/data_pipeline \
    MLFLOW_TRACKING_URI=file:///mlflow/mlruns \
    GIT_PYTHON_REFRESH=quiet

# Tracking store compartilhado entre mlflow e ml-trainer.
RUN mkdir -p /mlflow/mlruns && chmod +x /app/scripts/docker-train.sh

# Comando default: treina os modelos. O compose sobrescreve conforme o serviço
# (mlflow server / streamlit run para o dashboard, que reusa esta mesma imagem).
CMD ["/app/scripts/docker-train.sh"]
