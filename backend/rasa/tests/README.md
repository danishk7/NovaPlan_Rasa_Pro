# Rasa Tests

NovaPlan uses Rasa Pro CALM flows with `CompactLLMCommandGenerator` and `FlowPolicy`.

Recommended validation:

```bash
rasa data validate --config config.yml --domain domain.yml --data data/flows
rasa train --config config.yml --domain domain.yml --data data/flows --out models --fixed-model-name novaplan-test
rasa test nlu --model models/novaplan-test.tar.gz --nlu tests/test_nlu.yml --out ../results/rasa/nlu
rasa test core --model models/novaplan-test.tar.gz --stories tests/test_stories.yml --out ../results/rasa/core
rasa test e2e tests/e2e_test_cases.yml
```

Classic NLU and Core tests are compatibility smoke tests for this CALM assistant. The active model uses `CompactLLMCommandGenerator` and `FlowPolicy`, so low classic NLU/Core metrics are not by themselves production behavior evidence.

Rasa E2E tests are the primary dialogue validation asset. The suite covers stable utility, booking, validation, information, support, and cancel paths. An E2E run with zero discovered test cases is not valid evidence.

Rasa E2E tests require the action server to be reachable at the URL configured in `endpoints.yml`.

The E2E cases use the Rasa Pro `test_cases:` root schema. They avoid direct `action_executed` step assertions because the installed Rasa Pro 3.12 validator rejects that key in this project. Some utterance expectations reflect observed CALM runtime output in Hugging Face test runs.

The Hugging Face Docker startup test gate handles this automatically when `APP_ENV=TEST`.

```bash
APP_ENV=TEST /app/scripts/run_tests.sh
```

Runtime reports are generated under `/app/results`; Rasa result artifacts are copied to `/app/results/rasa` and also remain in Rasa's native `/app/rasa/results` folder.
