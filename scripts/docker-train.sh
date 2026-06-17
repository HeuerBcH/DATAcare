#!/bin/sh
# Treina os modelos na subida do docker compose (serviço one-shot ml-trainer).
#
# FORCE_ML_TRAIN=true  -> sempre treina (ignora modelos existentes)
# SKIP_ML_TRAIN=true   -> nunca treina (útil para subir a stack mais rápido)
set -e

DISEASE_MODEL="/app/data_pipeline/models/disease_classifier/MLmodel"
SEVERITY_MODEL="/app/data_pipeline/models/severity_classifier/MLmodel"

if [ "${SKIP_ML_TRAIN:-false}" = "true" ]; then
  echo "[ml-trainer] SKIP_ML_TRAIN=true — treino ignorado."
  exit 0
fi

if [ "${FORCE_ML_TRAIN:-false}" != "true" ] \
   && [ -f "$DISEASE_MODEL" ] && [ -f "$SEVERITY_MODEL" ]; then
  echo "[ml-trainer] Modelos já existem — pulando treino."
  echo "             (defina FORCE_ML_TRAIN=true para forçar novo treino)"
  exit 0
fi

# Cap de linhas p/ manter o treino dentro da memória do Docker (8GB padrão).
# 0 = usar todas as linhas. Ajuste via ML_MAX_ROWS no .env se tiver mais RAM.
MAX_ROWS="${ML_MAX_ROWS:-120000}"

echo "[ml-trainer] Iniciando treino (Random Forest + Árvore de Decisão)... (max_rows=${MAX_ROWS})"
exec python -m src.models.train --model all --search random --n-iter 10 --max-rows "$MAX_ROWS" "$@"
