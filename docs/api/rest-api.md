# REST API

PySOAR exposes a FastAPI REST layer for automation and integration with external systems.

## Start the server

```bash
pip install -r requirements-api.txt
python3 pysoar.py --serve-api --host 0.0.0.0 --port 8088
```

Docker (full lab profile):

```bash
make lab-full-up   # includes pysoar-api on port 8088
```

Interactive docs: `http://127.0.0.1:8088/docs`

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health |
| GET | `/playbooks` | List playbooks |
| GET | `/playbooks/{name}` | Playbook summary |
| POST | `/playbooks/{name}/validate` | Run validation |
| GET | `/playbooks/{name}/health` | Integration health for playbook |
| POST | `/playbooks/{name}/run` | Execute playbook (`{"once": true}`) |
| GET | `/integrations` | Enabled integrations |
| GET | `/scheduler/jobs` | List scheduled jobs |
| POST | `/scheduler/playbooks/{name}` | Schedule interval run |

## Example

```bash
curl -s http://127.0.0.1:8088/playbooks
curl -X POST http://127.0.0.1:8088/playbooks/test/run \
  -H 'Content-Type: application/json' \
  -d '{"once": true}'
```

## Background scheduler (CLI)

Run a playbook on an interval without the REST API:

```bash
python3 pysoar.py --scheduler test --interval 300 --once
```

Uses APScheduler in the foreground; press Ctrl+C to stop.
