#!/bin/bash
set -e

APP_ENV_NORMALIZED="$(printf '%s' "${APP_ENV:-PROD}" | tr '[:lower:]' '[:upper:]')"

if [ "$APP_ENV_NORMALIZED" != "TEST" ]; then
  echo "APP_ENV=${APP_ENV_NORMALIZED}. Skipping startup test suite."
  exit 0
fi

echo "APP_ENV=TEST. Running NovaPlan backend test suite before service startup."
mkdir -p /app/results/rasa /app/rasa/results
SUMMARY_FILE="/app/results/test_summary.txt"
REPORT_FILE="/app/results/backend_validation_report.md"
CSV_FILE="/app/results/test_evidence_summary.csv"
JSON_FILE="/app/results/evidence.json"
TABLES_FILE="/app/results/evidence_tables.json"
HTML_FILE="/app/results/evidence_report.html"
ACTION_SERVER_PID=""
PYTEST_STATUS="not_run"
RASA_TRAIN_STATUS="not_run"
RASA_NLU_STATUS="not_run"
RASA_CORE_STATUS="not_run"
RASA_E2E_STATUS="not_run"
RASA_E2E_LOG="/app/results/rasa/e2e/rasa_e2e_results.txt"

finish_summary() {
  sync_rasa_results
  python /app/scripts/generate_test_evidence.py || true
}

sync_rasa_results() {
  mkdir -p /app/results/rasa
  if [ -d /app/rasa/results/nlu ]; then
    rm -rf /app/results/rasa/nlu
    cp -R /app/rasa/results/nlu /app/results/rasa/nlu
  fi
  if [ -d /app/rasa/results/core ]; then
    rm -rf /app/results/rasa/core
    cp -R /app/rasa/results/core /app/results/rasa/core
  fi
}

cleanup_action_server() {
  if [ -n "$ACTION_SERVER_PID" ] && kill -0 "$ACTION_SERVER_PID" >/dev/null 2>&1; then
    kill "$ACTION_SERVER_PID" >/dev/null 2>&1 || true
    wait "$ACTION_SERVER_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup_action_server EXIT

cd /app
python -m pytest -v | tee /app/results/pytest_results.txt
PYTEST_STATUS="passed"

cd /app/rasa
rasa train \
  --config config.yml \
  --domain domain.yml \
  --data data/flows \
  --out models \
  --fixed-model-name novaplan-test
RASA_TRAIN_STATUS="passed"

TEST_MODEL="/app/rasa/models/novaplan-test.tar.gz"

rasa test nlu --model "$TEST_MODEL" --nlu data/nlu_test.yml --out results/nlu
RASA_NLU_STATUS="completed"
sync_rasa_results
echo "Rasa NLU results copied to /app/results/rasa/nlu"

if rasa test core --model "$TEST_MODEL" --stories tests/test_stories.yml --out results/core; then
  echo "Rasa Core compatibility tests completed."
  RASA_CORE_STATUS="completed"
else
  echo "WARNING: Rasa Core compatibility tests failed or are not supported by this CALM setup."
  RASA_CORE_STATUS="warning"
fi
sync_rasa_results
echo "Rasa Core results copied to /app/results/rasa/core"

echo "Starting temporary Rasa action server for E2E tests..."
python -m rasa_sdk --actions actions --port 5055 > /app/results/rasa_action_server_test.log 2>&1 &
ACTION_SERVER_PID="$!"

for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:5055/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

mkdir -p /app/results/rasa/e2e

if ! curl -fsS http://127.0.0.1:5055/health >/dev/null 2>&1; then
  echo "Rasa E2E tests failed: temporary action server did not become healthy." | tee "$RASA_E2E_LOG"
  RASA_E2E_STATUS="failed_action_server_unhealthy"
  finish_summary
  exit 1
fi

set +e
rasa test e2e tests/e2e_test_cases.yml 2>&1 | tee "$RASA_E2E_LOG"
E2E_EXIT=${PIPESTATUS[0]}
set -e

if grep -Eiq "0 passed, 0 failed|no test cases found" "$RASA_E2E_LOG"; then
  echo "Rasa E2E tests failed: zero test cases were discovered." | tee -a "$RASA_E2E_LOG"
  RASA_E2E_STATUS="failed_zero_tests"
  finish_summary
  exit 1
fi

if [ "$E2E_EXIT" -eq 0 ]; then
  echo "Rasa E2E tests completed."
  RASA_E2E_STATUS="completed"
else
  echo "Rasa E2E tests failed"
  RASA_E2E_STATUS="failed"
  finish_summary
  exit "$E2E_EXIT"
fi

finish_summary
