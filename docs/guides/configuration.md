# Configuration and secrets

## Integration configs

Templates live in `config/*.template.yaml`. Copy to `config/{name}.yaml` and set `enabled: true`.

Example:

```yaml
misp:
  enabled: true
  url: "https://misp.example.com"
  api_key_secret: true   # preferred — key stored in encrypted vault
  ssl: true
  verifycert: true
```

## Encrypted API keys

```bash
python3 pysoar.py --init-secrets
python3 pysoar.py --set-secret misp
python3 pysoar.py --migrate-secrets   # move existing plaintext keys
```

Vault location: `secrets/vault/{integration}.json` (gitignored).

## Environment variables

| Variable | Purpose |
|---|---|
| `PYSOAR_MOCK_INTEGRATIONS` | `1` enables in-process mocks |
| `PYSOAR_MASTER_KEY` | Fernet master key (Docker/CI) |
| `PYSOAR_SECRETS_PASSPHRASE` | Passphrase-derived master key |
| `PYSOAR_SECRETS_DIR` | Override secrets directory |
| `PYSOAR_{INTEGRATION}_API_KEY` | Per-integration runtime override |

## CLI flags

See README CLI reference for `--run-playbook`, `--list-playbooks`, and secrets commands.
