# Persistence, sensors, and orchestration

v0.7.0 adds the pieces required for 24/7 unattended operation on edge
hardware: durable state, environmental condition triggers, and playbook
composition.

## State store (SQLite)

`core/state_store.py` persists to a single SQLite file (WAL mode, stdlib
only — suitable for Raspberry Pi / SD card deployments).

| Table | Purpose |
|---|---|
| `runs` / `steps` | Every playbook execution with outcomes and shared_data snapshot |
| `observables` | Deduplicated indicator memory (`first_seen`, `last_seen`, `times_seen`, sources) |
| `actions` | Idempotency ledger — fingerprint of each successful action |
| `kv` | Key/value state (sensor baselines etc.) |

Configuration:

```bash
export PYSOAR_STATE_DB=/var/lib/pysoar/state.db   # default: ./pysoar_state.db
export PYSOAR_STATE_DB=off                        # disable persistence
```

Inspect history:

```bash
python3 pysoar.py --history 20
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8088/runs
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8088/observables?type=ip-dst
```

## Idempotent actions

Manifests may declare:

```yaml
idempotent: true
dedupe_window_seconds: 3600
```

An identical invocation (same integration, function, and arguments) that
succeeded within the window is skipped and treated as success. This is what
makes continuously looping playbooks safe: the same IP is not re-blocked and
the same notification is not re-sent every cycle.

## Sensors and condition triggers

Sensors (`sensors/`) are cheap environmental detectors polled on an
interval. Each `poll()` returns numeric metrics plus the observables that
explain them. The reference implementation is `beacon_detector`, which
flags hosts contacting the same destination at suspiciously regular
intervals (C2 heartbeat pattern) using inter-arrival statistics:

- feed it a JSONL connection log via `PYSOAR_CONN_LOG`
  (`{"src": "10.0.0.5", "dst": "203.0.113.9", "ts": 1719900000}` per line), or
- call `sensor.observe(src, dst, ts)` programmatically.

A perfectly regular heartbeat has coefficient of variation near 0 and
scores near 1.0.

### Step-level sensor trigger

```yaml
- function: create_misp_event
  trigger:
    type: condition
    condition:
      type: sensor
      sensor: beacon_detector
      when: "beacon_score >= 0.8 and duration_hours >= 2"
      mode: skip        # or wait (+ poll_interval / timeout)
```

When the condition fires, the sensor's observables (beaconing source and
destination) are injected into `shared_data`, and metrics appear under
`shared_data['sensor_metrics']`.

### Scheduler-level watch (24/7 pattern)

```python
from scheduler import PlaybookScheduler

sched = PlaybookScheduler(max_concurrent=4)
sched.schedule_condition(
    'contain_beacon',            # playbook to fire
    'beacon_detector',           # sensor to watch
    'beacon_score >= 0.8 and duration_hours >= 2',
    poll_seconds=300,
)
sched.start()
```

The job polls forever at negligible cost and launches the playbook — seeded
with the offending observables — only when the environment condition is met.

Condition expressions support `>= <= == != > <` clauses joined by
`and` / `or`. They are parsed, never `eval`'d.

## Playbook composition

A step named `run_playbook:<child>` runs another playbook inline:

```yaml
- function: run_playbook:contain_host
  trigger:
    type: always
  on_success: run_playbook:notify_operator
  on_fail: halt_playbook
```

Semantics:

- the child receives a deep copy of the parent's `shared_data` and its
  results are merged back on completion
- recursion and nesting beyond depth 5 are refused at runtime, and the
  validator rejects self-references and missing children
- child runs are recorded as separate runs in the state store

This is how a small-enterprise SOC tier structure is replicated: a triage
playbook enriches and scores, then calls containment and notification
playbooks as children — 24/7, with the human involved only where the
playbook graph says so.

## Scheduler guardrails

`PlaybookScheduler` now enforces a global concurrency cap
(`max_concurrent`, default 4) and skips a scheduled run when the same
playbook is already running.
