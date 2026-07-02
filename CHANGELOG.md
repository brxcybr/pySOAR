# Changelog

All notable changes to PySOAR are documented in this file.

## [0.7.0] - 2026-07-02

### Added — persistence, sensors, orchestration
- `core/state_store.py` SQLite persistence: run history, step records, deduplicated observable memory, action idempotency ledger, key/value state (`PYSOAR_STATE_DB`, WAL mode, stdlib only)
- Idempotent actions: manifests may declare `idempotent: true` + `dedupe_window_seconds`; identical successful invocations within the window are skipped (enabled for `add_firewall_rule`, `ban_ip`)
- `sensors/` plugin type with `beacon_detector` reference sensor (inter-arrival statistics for C2 heartbeat detection; JSONL log via `PYSOAR_CONN_LOG` or programmatic feed)
- `sensor` condition type for triggers: `when: "beacon_score >= 0.8 and duration_hours >= 2"` (safe expression parser, no eval); firing sensors inject their observables into shared_data
- `PlaybookScheduler.schedule_condition()` — 24/7 watch pattern: poll a sensor and launch a playbook (seeded with sensor observables) when the condition is met
- Playbook composition: `run_playbook:<child>` steps run child playbooks with shared_data passing and merge-back; recursion/depth guards; validator checks for self-reference and missing children
- Scheduler guardrails: global concurrency cap (`max_concurrent`) and per-playbook already-running skip
- CLI: `--history [N]`, `--list-sensors`; API: `GET /runs`, `GET /runs/{id}`, `GET /observables`, `GET /sensors`
- Documentation: [docs/architecture/persistence-and-orchestration.md](docs/architecture/persistence-and-orchestration.md)

### Fixed
- `--once` / `max_cycles` never terminated for playbooks that loop back to a mid-graph step instead of the first step; cycle detection now tracks visited steps
- `evaluate_condition` no longer discards the caller's empty shared_data dict (sensor observable injection was lost on first steps)
- Responder manifests no longer map bare scalar results onto observable keys (a `True` return could stomp `ip-dst` in shared_data)

## [0.6.1] - 2026-07-02

### Fixed — CIDM adapter hardening
- OpenIOC: indicator pattern now uses the indicator `id` attribute (was a leaked loop variable); XML export escapes special characters
- YARA: brace-aware rule parsing handles hex-string patterns (`{ 6A 40 }`), rule tags (`rule x : trojan {`), and `global`/`private` modifiers
- SIGMA: empty-bundle export no longer crashes; IOC extraction validates IPs (`ipaddress`, incl. IPv6) and classifies URLs/domains/hashes instead of emitting generic noise
- STIX 2.x: export produces valid STIX 2.1 (object `id`s, `created`/`modified`, indicator `valid_from`/`pattern_type`); IPv6 SCOs parsed and exported as `ipv6-addr`; file hashes typed by length (MD5/SHA-1/SHA-256)
- Observables adapter: only promotes standard observable keys from shared_data (skips `feed_id` etc.)
- CIDM model: tolerant `from_dict` with clear `ValueError` for malformed bundle content (clean API 400s instead of raw `KeyError`)

## [0.6.0] - 2026-07-01

### Added — CIDM threat intelligence hub
- `core/cidm/` Common Information Data Model for normalizing intel formats
- Adapters: STIX 2.x, OpenIOC, YARA, SIGMA, MITRE ATT&CK, OpenC2, observables
- Stub registrations: TAXII, MAEC, VERIS, CybOX, IDMEF, IODEF, CAPEC, intel.dat
- `IntelConverter` hub for format-to-format translation
- CLI: `--list-intel-formats`, `--convert-intel`, `--from-format`, `--to-format`
- REST: `GET /intel/formats`, `POST /intel/convert`
- Playbook shared_data `cidm_bundle` support with observable bridge
- Optional `pysoar[intel]` extra (`stix2`)
- Documentation: [docs/architecture/cidm.md](docs/architecture/cidm.md)

## [0.5.0] - 2026-07-01

### Added — Phase 0 foundation
- `core/` package: plugin registry, action manifests, observable schema v1, audit log, API auth
- YAML manifests under `integrations/manifests/` for MISP, pfSense, CrowdSec actions
- Entry-point plugin registration (`pysoar.integrations`)
- `--list-actions` CLI and `GET /actions` API endpoint
- Optional JSONL audit log (`PYSOAR_AUDIT_LOG`)
- REST API Bearer token auth (`PYSOAR_API_TOKEN`)
- Optional dependency groups: `analyzers`, `ansible` (placeholders), `all`
- Phase 0 documentation and tests

### Changed
- `integrations/dispatch.py` reads producer/input/output/risk data from manifests
- `playbook_validator.py` uses manifest risk tiers
- `IntegrationManager` loads plugins via registry
- Playbook execution writes audit events and syncs observable schema

## [0.4.0] - 2026-07-01

### Added
- FastAPI REST API (`api_server.py`) with playbook run, validate, health, and scheduler endpoints
- Background playbook scheduler (`scheduler.py`) with CLI `--scheduler` flag
- Full Docker lab profile: MISP, CrowdSec, and webhook mock services + `pysoar-api`
- `lab/scripts/seed-misp.sh` and `lab/scripts/generate-certs.sh`
- Ansible bootstrap playbook (`lab/ansible/`)
- GNS3 topology documentation (`docs/lab/gns3-topology.md`)
- `requirements-api.txt` optional dependencies
- API and scheduler tests

### Changed
- `lab/docker-compose.yml` extended with `--profile full`
- Bootstrap script supports `LAB_PROFILE=full`
- Makefile targets: `lab-full-up`, `lab-full-down`, `lab-seed-misp`, `lab-certs`

## [0.3.0] - 2026-07-01

### Added
- Docker lab stack (`lab/docker-compose.yml`) with pfSense API mock service
- `Makefile` targets: `lab-up`, `lab-test`, `lab-down`, `test`, `bootstrap`
- GitHub Actions CI (pytest + Docker lab smoke test)
- Documentation site under `docs/` and streamlined README
- `integrations/base.py` shared mock-mode helpers and `IntegrationBase` contract
- pfSense in-process mock mode (parity with MISP mock mode)
- `pyproject.toml` with correct packaging metadata
- `CHANGELOG.md` and `CONTRIBUTING.md`

### Changed
- MISP is optional — core no longer fails when MISP is disabled
- `setup.py` bumped to v0.3.0; includes `cryptography` and root `py_modules`
- README refactored; legacy install guide moved to `docs/getting-started/full-install-guide.md`

### Fixed
- `IntegrationManager.save()` YAML structure (nested dict bug)
- Duplicate `_integration_mgr` assignment in `ConfigurationManager`

## [0.2.0] - Remediation branch

### Added
- Playbook execution pipeline (`resolve_callable`, shared data dispatch)
- Playbook validator and integration health checks
- Trigger system (`always`, `time`, `condition`)
- Encrypted API key storage (`secrets_manager.py`)
- Plugins: webhook, CrowdSec, OPNsense
- CLI: `--run-playbook`, `--list-playbooks`, secrets commands
- Test suite (28+ tests)

### Changed
- PyMISP upgraded to 2.5.x (PyPI install)
- TUI fixes: edit playbook, visualize, launch validation

## [0.1.0] - Initial POC

- MISP + pfSense YAML-driven playbook
- Curses TUI menu system
- Manual GNS3 lab documentation
