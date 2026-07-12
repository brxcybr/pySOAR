# Contributing to PySOAR

Thank you for contributing to PySOAR. This project targets edge/SOHO SOAR use cases and welcomes improvements to integrations, playbooks, documentation, and lab automation.

## Development setup

```bash
git clone https://github.com/brxcybr/pySOAR.git
cd pySOAR
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
make test
```

## Pull request checklist

Before opening a PR, ensure:

- [ ] Tests pass: `make test`
- [ ] New behavior has tests where practical
- [ ] `CHANGELOG.md` updated under `[Unreleased]` or the current version
- [ ] User-facing changes documented in `docs/` or README
- [ ] Config template comments updated if integration fields change
- [ ] No secrets, API keys, or local configs committed (`config/*.yaml`, `secrets/`)

## Documentation expectations

| Change type | Update |
|---|---|
| New CLI flag | README + `docs/guides/configuration.md` |
| New integration | Template YAML + `docs/guides/adding-integrations.md` |
| Playbook schema | `docs/guides/playbook-authoring.md` |
| Lab/Docker | `docs/lab/` + `lab/README.md` |
| Architecture | `docs/architecture/overview.md` |

## Code style

- Match existing module style and naming in the file you edit
- Prefer focused diffs — avoid unrelated refactors in the same PR
- Use mock mode (`PYSOAR_MOCK_INTEGRATIONS=1`) for integration tests when possible

## Adding an integration

1. Create `integrations/{name}_functions.py` with a `{Name}Function` class
2. Add `config/{name}.template.yaml`
3. Register playbook functions in the template
4. Add dispatch aliases in `integrations/dispatch.py` if needed
5. Add health probe support in `integrations/health.py`
6. Add tests with mock HTTP or in-process mock mode

See [docs/guides/adding-integrations.md](docs/guides/adding-integrations.md).

## Reporting issues

Include Python version, OS, playbook name, relevant log excerpts from `PySOAR.log`, and whether mock mode was enabled.
