# Docker lab

The Docker lab provides a one-command test environment without GNS3 or a real pfSense VM.

## Services

| Service | Purpose |
|---|---|
| `pysoar` | Main SOAR runner (built from repo `Dockerfile`) |
| `pfsense-mock` | FastAPI stub of pfSense API v1 endpoints |

By default `PYSOAR_MOCK_INTEGRATIONS=1` so MISP and pfSense both use in-process mocks inside the PySOAR container. The pfSense mock container is available for HTTP-level integration testing when mock env is disabled.

### Full profile

Start all mock services plus the REST API:

```bash
make lab-full-up
curl http://127.0.0.1:8088/health
make lab-full-down
```

Services in `--profile full`:

| Service | Port | Purpose |
|---|---|---|
| `pysoar-api` | 8088 | FastAPI REST server |
| `pfsense-mock` | 8080 | pfSense API stub |
| `misp-mock` | 8082 | MISP API stub |
| `crowdsec-mock` | 8081 | CrowdSec LAPI stub |
| `webhook-sink` | 9000 | Webhook receiver |

Use `LAB_PROFILE=full make bootstrap` to install `lab/config/full.yaml` integration configs.

## Quick start

```bash
cp lab/.env.example lab/.env
make lab-up      # bootstrap configs + start containers
make lab-test    # run test playbook once
make lab-down    # tear down
```

## Bootstrap

`lab/scripts/bootstrap.sh`:

- Copies `lab/config/lab.yaml` into `config/` (if files do not exist)
- Creates `secrets/.master.key` when missing (host needs `PyYAML` + `cryptography`)

## Files

```
lab/
├── docker-compose.yml
├── .env.example
├── config/lab.yaml
├── mocks/pfsense/     # HTTP mock service
└── scripts/
    ├── bootstrap.sh
    └── wait-healthy.sh
```

## Full network lab

For real pfSense in GNS3, MISP Docker, and certificate setup, see [full install guide](../getting-started/full-install-guide.md).
