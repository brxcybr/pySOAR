# PySOAR lab

See [docs/lab/docker-compose.md](../docs/lab/docker-compose.md) and [docs/guides/testing.md](../docs/guides/testing.md).

```bash
cp .env.example .env
make lab-up      # or: make lab-full-up
make lab-test
make lab-down    # or: make lab-full-down
```

`lab/.env` and generated `config/*.yaml` files are local-only — do not commit them.
