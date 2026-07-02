# Changelog

All notable changes to PySOAR are documented in this file.

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
