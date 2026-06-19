#!/bin/bash
set -e

export RASA_LICENSE="${RASA_LICENSE:-${RASA_PRO_LICENSE:-}}"
MODEL="/app/rasa/models/novaplan.tar.gz"

echo "Ensuring Rasa model exists at $MODEL ..."
/app/scripts/train_rasa.sh

if [ ! -f "$MODEL" ]; then
  echo "ERROR: No model at $MODEL. Cannot start Rasa server."
  exit 1
fi

echo "Starting Rasa server with model $MODEL"
cd /app/rasa
exec rasa run \
  --enable-api \
  --cors "*" \
  --port 5005 \
  --model "$MODEL" \
  --endpoints endpoints.yml \
  --credentials credentials.yml
