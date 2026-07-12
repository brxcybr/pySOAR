# Testing

## Unit tests

```bash
pip install -r requirements-dev.txt
make test
# or
python3 -m pytest tests/ -q
```

## Mock integrations (in-process)

Set `PYSOAR_MOCK_INTEGRATIONS=1` (and optionally `PYSOAR_MOCK_ANALYZERS=1`) or leave placeholder values (`{API_KEY}`) in config URLs/keys.

Both MISP and pfSense support in-process mock mode:

- MISP returns static `MOCK_INDICATORS`
- pfSense simulates firewall rule create/apply in memory

```bash
export PYSOAR_MOCK_INTEGRATIONS=1 PYSOAR_MOCK_ANALYZERS=1
python3 pysoar.py --run-playbook test --once
```

## Docker lab — in-process mocks

```bash
cp lab/.env.example lab/.env
# keep PYSOAR_MOCK_INTEGRATIONS=1
make lab-test
```

This builds containers, bootstraps configs from `lab/config/lab.yaml`, and runs the `test` playbook once.

## Docker lab — HTTP mocks (closer to live)

Exercises real HTTP clients against stub MISP/pfSense/CrowdSec/webhook services:

```bash
cp lab/.env.example lab/.env
# set PYSOAR_MOCK_INTEGRATIONS=0 (keep PYSOAR_MOCK_ANALYZERS=1 unless you have vendor keys)
make lab-full-up
docker compose --env-file lab/.env -f lab/docker-compose.yml --profile full run --rm \
  -e PYSOAR_MOCK_INTEGRATIONS=0 \
  pysoar-api --run-playbook test --once
curl -s http://127.0.0.1:18080/api/v1/firewall/rule
make lab-full-down
```

Notes:

- Host port for pfSense mock is **18080** (container listens on 8080).
- Bootstrap installs `lab/config/full.yaml` into `config/*.yaml` when missing; those runtime files are gitignored.
- Never commit `lab/.env`, `secrets/`, `certs/`, or filled-in `config/*.yaml`.

## CI

GitHub Actions runs pytest, `pip-audit`, and a Docker lab smoke test on push/PR (see `.github/workflows/ci.yml`).

## Writing integration tests

- Use `responses` library for HTTP mocking (see `tests/test_pfsense_mock.py`)
- Use in-process mock mode for end-to-end playbook tests
- Avoid PyAutoGUI TUI tests in CI (optional, fragile)
