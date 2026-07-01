# Playbook authoring

Playbooks are YAML files in `playbooks/` with a top-level `Playbook:` key.

## Minimal example

```yaml
Playbook:
  name: example
  enabled: true
  integration_dependencies:
    - misp
    - pfsense
  logic:
    - function: get_misp_event_by_type
      data_dependencies:
        - ip-dst
      trigger:
        type: always
      on_success: add_firewall_rule
      on_fail: halt_playbook
    - function: add_firewall_rule
      trigger:
        type: always
      on_success: halt_playbook
      on_fail: halt_playbook
    - function: halt_playbook
      trigger:
        type: always
```

## Triggers

| Type | Fields | Behavior |
|---|---|---|
| `always` | — | Run immediately |
| `time` | `duration` (seconds) | Wait before running |
| `condition` | `check`, `mode` | Declarative gate (see `triggers.py`) |

## Branch targets

- Function name — jump to that step
- `halt_playbook` — stop execution
- `next` — advance sequentially
- `loop` — restart cycle

## Validation

Before launch, PySOAR validates:

- All referenced functions exist and integrations are enabled
- Data producers precede consumers
- High-risk functions are not unguarded first steps
- No dangling branch targets

Use `--run-playbook NAME --once` for single-cycle testing.
