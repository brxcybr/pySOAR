FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYSOAR_SECRETS_DIR=/app/secrets

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt requirements-api.txt setup.py pyproject.toml ./
COPY integrations ./integrations
COPY classes.py menu.py pysoar.py secrets_manager.py triggers.py playbook_validator.py scheduler.py api_server.py ./

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-api.txt \
    && pip install --no-cache-dir .

COPY playbooks ./playbooks
COPY lab ./lab
COPY config ./config

RUN chmod +x lab/scripts/bootstrap.sh lab/scripts/wait-healthy.sh

ENTRYPOINT ["python3", "pysoar.py"]
CMD ["--list-playbooks"]
