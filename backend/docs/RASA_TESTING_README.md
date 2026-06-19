# NovaPlan Rasa Testing

NovaPlan is configured as a Rasa Pro CALM assistant. The active `config.yml` uses `CompactLLMCommandGenerator` and `FlowPolicy`, and flows live under `data/flows/`.

## Configuration Finding

| Area | Finding |
|---|---|
| Dialogue engine | Rasa Pro CALM |
| Pipeline | `CompactLLMCommandGenerator` only |
| Policies | `FlowPolicy` only |
| Classic NLU pipeline | Not configured |
| Classic stories/rules | Not used as the primary dialogue model |
| Flows | Primary behavior lives under `data/flows/` |
| Domain intents | Present for compatibility and documentation, but not trained by a classic NLU classifier in the active config |

Because there is no classic NLU classifier in `config.yml`, classic NLU accuracy/F1 can be weak or meaningless for this assistant. Pytest and Rasa E2E are the stronger evidence types for current behavior.

## License and LLM Variables

Use `RASA_LICENSE` as the required Hugging Face secret for Rasa Pro. The project does not require `RASA_PRO_TOKEN`.

OpenRouter is configured in `endpoints.yml` through:

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | API key used by the `llm_models_grp` model group |
| `LLM_MODEL_NAME` | Model name passed to the OpenRouter-compatible OpenAI provider |

No extra production flag is required. If your installed Rasa Pro CLI requires additional test-only flags, confirm with `rasa test --help` and `rasa test e2e --help` for that exact installed version.

## Created Test Assets

| File | Purpose |
|---|---|
| `tests/test_nlu.yml` | Compatibility NLU test examples using only domain intents |
| `data/nlu_test.yml` | Duplicate compatibility NLU path retained for existing commands |
| `tests/test_stories.yml` | Classic Core compatibility smoke tests only |
| `tests/e2e_test_cases.yml` | Discoverable Rasa Pro CALM E2E `test_cases` covering stable utility, booking, validation, information, support, and cancel paths |

Some E2E expectations, such as `utter_cannot_handle`, `utter_human_handoff_not_available`, and `utter_ask_rephrase`, reflect observed Rasa Pro CALM runtime behavior from Hugging Face test runs. They are retained as runtime evidence expectations even when the classic domain also defines stable responses such as `utter_out_of_scope` and `utter_goodbye`. Because CALM uses LLM command generation, these tests should be adjusted to current runtime output when Hugging Face evidence shows stable changed behavior.

Unstable CALM paths such as single-turn `help`, bot identity, same-origin validation from one free-form sentence, and mid-flow `modify` are excluded from automated E2E evidence because the Hugging Face runtime has returned different valid CALM command outcomes across runs. Keep those paths as manual observation items until their runtime behavior is stable.

## Commands

Run from `backend/rasa`:

```bash
APP_ENV=TEST
rasa train --config config.yml --domain domain.yml --data data/flows --out models --fixed-model-name novaplan-test
rasa test nlu --model models/novaplan-test.tar.gz --nlu tests/test_nlu.yml --out ../results/rasa/nlu
rasa test core --model models/novaplan-test.tar.gz --stories tests/test_stories.yml --out ../results/rasa/core
rasa test e2e tests/e2e_test_cases.yml
```

When deployed to Hugging Face Docker, these tests only run during startup when `APP_ENV=TEST`. Leave `APP_ENV` unset or set it to `PROD` for normal production deployment.

The Hugging Face runtime test process generates the markdown report and CSV evidence under `/app/results`. Rasa-generated reports are written by Rasa under `/app/rasa/results` and copied by the test script to `/app/results/rasa`.

Structured report artifacts are generated under `/app/results/evidence_report.html`, `/app/results/evidence.json`, and `/app/results/evidence_tables.json`. Use these as primary evidence instead of raw logs.

## CALM Compatibility Note

Classic NLU/Core tests are compatibility evidence only. They may show weak metrics because this project is not a classic NLU/story-first assistant. Rasa E2E is the primary Rasa Pro CALM dialogue validation method.

An E2E run that reports zero discovered test cases is not valid evidence. The E2E file must use `test_cases:` as the root key and must not include the classic training-data root key `version: "3.1"`.

## Production Note

Do not run tests during production startup. Use `APP_ENV=TEST` only in a test deployment/environment. Production should leave `APP_ENV` unset or set it to `PROD`.
