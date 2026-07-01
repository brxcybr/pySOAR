# Adding integrations

## Steps

1. **Template** — `config/{name}.template.yaml` with `enabled`, `url`, `api_key`, `playbook_functions`, etc.
2. **Module** — `integrations/{name}_functions.py` with class `{Name}Function` (note capitalization: `MispFunction`, `PfsenseFunction`).
3. **Dispatch** — add function aliases in `integrations/dispatch.py` if playbook names differ from method names.
4. **Health** — add probe path in `integrations/health.py` if HTTP connectivity check is applicable.
5. **Mock mode** — use `integrations/base.use_mock_mode()` for offline testing.
6. **Tests** — add `tests/test_{name}_mock.py`.

## IntegrationBase

```python
from integrations.base import use_mock_mode, IntegrationBase
```

Shared mock detection checks `PYSOAR_MOCK_INTEGRATIONS` and `{placeholder}` config values.

## Playbook functions

Methods on your function class become playbook steps. Return values are merged into shared data when they are dicts containing known indicator keys (`ip-dst`, etc.).

See existing integrations for patterns: `misp_functions.py`, `pfsense_functions.py`, `webhook_functions.py`.
