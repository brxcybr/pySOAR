# Phase 0 foundation

PySOAR Phase 0 establishes extensibility primitives used by all future plugins (analyzers, Ansible, full API coverage).

## Components

| Module | Purpose |
|---|---|
| `core/plugin_registry.py` | Entry-point discovery for integrations |
| `core/manifests.py` | YAML action catalog loader |
| `core/observables.py` | Shared-data observable schema v1 |
| `core/audit_log.py` | Optional JSONL execution audit |
| `core/api_auth.py` | Bearer token auth for REST API |

## Action manifests

Manifests live under `integrations/manifests/{integration}/*.yaml`:

```yaml
name: add_firewall_rule
integration: pfsense
category: responder
risk: high
producer: false
inputs:
  - name: ip-dst
    maps_to: src
outputs:
  - ip-dst
```

Manifests drive:

- Dispatch input/output mapping
- Playbook validator risk tiers
- `pysoar --list-actions` and `GET /actions`

## Plugin entry points

Third-party integrations register via `pyproject.toml`:

```toml
[project.entry-points."pysoar.integrations"]
mytool = "mytool_plugin:MytoolFunction"
```

## Observable schema v1

Playbook `shared_data` may include:

```yaml
schema_version: 1
observables:
  - type: ip-dst
    value: 203.0.113.10
    sources: [misp]
    enrichment: {}
ip-dst: 203.0.113.10   # legacy flat keys remain supported
```

## Audit log

```bash
export PYSOAR_AUDIT_LOG=./PySOAR.audit.jsonl
python3 pysoar.py --run-playbook test --once
```

Set `PYSOAR_AUDIT_LOG=off` to disable.

## API authentication

```bash
export PYSOAR_API_TOKEN=your-secret-token
python3 pysoar.py --serve-api
curl -H "Authorization: Bearer your-secret-token" http://127.0.0.1:8088/playbooks
```

`/health`, `/docs`, and `/openapi.json` remain public when auth is enabled.

## Optional dependency groups

```bash
pip install pysoar[api]       # REST + scheduler HTTP stack
pip install pysoar[dev]       # pytest, responses
pip install pysoar[all]       # api + dev
```

Future groups: `analyzers`, `ansible` (placeholders in v0.5.0).

## CLI

```bash
python3 pysoar.py --list-actions
```
