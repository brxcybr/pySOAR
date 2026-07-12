.PHONY: install test lab-up lab-test lab-down lab-logs docker-build bootstrap

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install -e .

test:
	python3 -m pytest tests/ -q

bootstrap:
	bash lab/scripts/bootstrap.sh

lab-up: bootstrap
	docker compose --env-file lab/.env -f lab/docker-compose.yml --profile lab up -d --build
	bash lab/scripts/wait-healthy.sh pfsense-mock 90

lab-test: lab-up
	docker compose --env-file lab/.env -f lab/docker-compose.yml --profile lab run --rm pysoar --run-playbook test --once

lab-down:
	docker compose --env-file lab/.env -f lab/docker-compose.yml --profile lab down -v

lab-logs:
	docker compose --env-file lab/.env -f lab/docker-compose.yml --profile lab logs -f

lab-full-up:
	LAB_PROFILE=full $(MAKE) bootstrap
	docker compose --env-file lab/.env -f lab/docker-compose.yml --profile full up -d --build
	bash lab/scripts/wait-healthy.sh pfsense-mock 90

lab-full-down:
	docker compose --env-file lab/.env -f lab/docker-compose.yml --profile full down -v

lab-seed-misp:
	bash lab/scripts/seed-misp.sh

docker-build:
	docker build -t pysoar:local .
