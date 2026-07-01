# Changelog

All notable changes to PySOAR are documented in this file.

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
