# NovaPlan Test Evidence Notes

## Evidence Types

| Evidence | Current Meaning |
|---|---|
| Pytest | Valid unit-level backend and Rasa action evidence. External APIs and Neon DB are mocked. |
| Rasa NLU | Compatibility-only evidence. The active `config.yml` does not configure a classic NLU classifier. |
| Rasa Core | Compatibility-only evidence. The active assistant uses CALM flows and `FlowPolicy`, not classic story/rule policy behavior. |
| Rasa E2E | Primary Rasa dialogue evidence for this CALM assistant. |

Structured evidence endpoints are preferred for assignment reporting:

| Endpoint | Evidence |
|---|---|
| `/api/test-results/report.html` | Human-readable HTML report with dataframe-style evidence table |
| `/api/test-results/evidence.json` | Machine-readable summary for notebooks or reports |
| `/api/test-results/evidence/tables` | JSON table rows suitable for dataframe rendering |
| `/api/test-results/evidence.csv` | CSV dataframe-style summary |

Raw pytest/Rasa logs remain available as supporting artifacts, but they are not the primary evidence format.

## Invalid Evidence Conditions

| Result | Interpretation |
|---|---|
| `pytest` failures | Invalid backend unit evidence until fixed. |
| Rasa NLU `0.0` accuracy/F1 | Expected if testing a CALM model without a classic NLU classifier; do not use as primary quality evidence. |
| Rasa Core failed stories caused by repeated `action_listen` | Classic Core tests are not aligned with CALM flows; treat as compatibility-only. |
| Rasa E2E `0 passed, 0 failed` or `no test cases found` | Invalid evidence. The E2E files were not discovered or are in the wrong format. |

## Current Rasa Test Assets

| File | Purpose |
|---|---|
| `rasa/tests/test_nlu.yml` | Domain-intent compatibility NLU examples |
| `rasa/data/nlu_test.yml` | Duplicate compatibility NLU path for legacy commands |
| `rasa/tests/test_stories.yml` | Classic Core compatibility smoke tests |
| `rasa/tests/e2e_test_cases.yml` | CALM E2E dialogue test cases for stable utility, booking, validation, information, support, and cancel paths |

The E2E file follows the installed Rasa Pro `test_cases:` schema and intentionally avoids unsupported step keys such as direct `action_executed` assertions. Some expected utterances and slot assertions are based on observed CALM runtime output from Hugging Face test runs rather than classic story predictions.

Unstable CALM paths are not included in automated pass/fail evidence. Help, bot identity, same-origin validation from a single free-form sentence, and mid-flow modify requests have produced different valid CALM outcomes across Hugging Face runs.

## Recommended Evidence Priority

1. Pytest for deterministic unit coverage.
2. Rasa E2E for CALM dialogue behavior.
3. Rasa train/data validation for configuration validity.
4. Classic NLU/Core only as compatibility smoke checks.
