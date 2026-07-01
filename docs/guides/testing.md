# Testing

## Unit tests

```bash
pip install -r requirements-dev.txt
make test
# or
python3 -m pytest tests/ -q
```

## Mock integrations

Set `PYSOAR_MOCK_INTEGRATIONS=1` or leave placeholder values (`{API_KEY}`) in config URLs/keys.

Both MISP and pfSense support in-process mock mode:

- MISP returns static `MOCK_INDICATORS`
- pfSense simulates firewall rule create/apply in memory

## Docker lab smoke test

```bash
cp lab/.env.example lab/.env
make lab-test
```

This builds containers, bootstraps configs, and runs `test` playbook once.

## CI

GitHub Actions runs pytest and a Docker lab smoke test on push/PR (see `.github/workflows/ci.yml`).

## Writing integration tests

- Use `responses` library for HTTP mocking (see `tests/test_pfsense_mock.py`)
- Use in-process mock mode for end-to-end playbook tests
- Avoid PyAutoGUI TUI tests in CI (optional, fragile)
