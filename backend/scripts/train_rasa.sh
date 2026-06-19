#!/bin/bash
set -e

export RASA_LICENSE="${RASA_LICENSE:-${RASA_PRO_LICENSE:-}}"
MODEL="/app/rasa/models/novaplan.tar.gz"
mkdir -p /app/rasa/models

if [ -f "$MODEL" ]; then
  echo "Rasa model already present. Skipping training."
  exit 0
fi

if [ -z "$RASA_LICENSE" ]; then
  echo "ERROR: RASA_LICENSE is not set. Cannot train the model."
  exit 1
fi

echo "Training Rasa CALM model. First boot may take several minutes..."
cd /app/rasa
if ! rasa train \
  --config config.yml \
  --domain domain.yml \
  --data data/flows \
  --out models/ \
  --fixed-model-name novaplan; then
  echo "ERROR: rasa train failed. Check flow YAML under data/flows/"
  exit 1
fi

if [ ! -f "$MODEL" ]; then
  echo "ERROR: rasa train finished but $MODEL was not created."
  exit 1
fi

echo "Model trained: $MODEL"
