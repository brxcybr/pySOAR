# Architecture overview

PySOAR is a stateless SOAR runner: configuration and playbooks live on disk; execution passes a shared data dictionary between integration steps.

## Components

| Module | Role |
|---|---|
| `pysoar.py` | CLI entry point |
| `menu.py` | Curses TUI |
| `classes.py` | ConfigurationManager, Integration, PlaybookManager |
| `integrations/dispatch.py` | Function resolution, kwargs mapping, shared data merge |
| `playbook_validator.py` | Structural and safety validation before launch |
| `integrations/health.py` | Config and connectivity probes |
| `triggers.py` | Step trigger evaluation |
| `secrets_manager.py` | Encrypted API key vault |

## Execution flow

1. Load enabled integrations from `config/*.yaml`
2. Resolve API keys via SecretStore (vault, env override, or plaintext)
3. Load playbook YAML from `playbooks/`
4. Validate graph integrity and data-flow order
5. Health-check required integrations
6. For each step: evaluate trigger → call integration method → merge result into `shared_data` → branch

## Shared data pipeline

Playbook steps pass indicator data through a runtime dictionary. Example POC path:

```
enable_threat_feed → get_misp_event_by_type (produces ip-dst) → add_firewall_rule (consumes ip-dst)
```

`integrations/dispatch.py` classifies functions as producers or consumers and maps kwargs automatically.

## Integration plugin pattern

Each integration provides:

- `config/{name}.template.yaml` — configuration schema
- `integrations/{name}_functions.py` — `{Name}Function` class with playbook methods

Integrations may implement in-process mock mode via `integrations/base.py` when config contains placeholders or `PYSOAR_MOCK_INTEGRATIONS=1`.

## Deployment modes

| Mode | Use case |
|---|---|
| Native | Raspberry Pi / edge VM |
| Docker | Lab and CI (`Dockerfile`, `lab/docker-compose.yml`) |
| Mock | Offline dev without live MISP/pfSense |
| GNS3 lab | Full network POC with real pfSense VM |
