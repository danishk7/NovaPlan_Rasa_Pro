#!/bin/bash
set -e

export PYTHONPATH="/app:/app/rasa/actions${PYTHONPATH:+:$PYTHONPATH}"

export PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-http://127.0.0.1:8501}"
export TARGET_RASA_URL="${TARGET_RASA_URL:-http://127.0.0.1:5005}"
export ACTION_SERVER_URL="${ACTION_SERVER_URL:-http://127.0.0.1:5055}"
export RASA_LICENSE="${RASA_LICENSE:-${RASA_PRO_LICENSE:-}}"
export APP_ENV="${APP_ENV:-PROD}"

if [ -z "$RASA_LICENSE" ]; then
  echo "WARNING: RASA_LICENSE is not set. Rasa Pro train/run will fail."
fi

/app/scripts/run_tests.sh

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/novaplan.conf
