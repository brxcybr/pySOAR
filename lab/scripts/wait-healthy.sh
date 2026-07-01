#!/usr/bin/env bash
set -euo pipefail

SERVICE="${1:-pfsense-mock}"
TIMEOUT="${2:-60}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not available; skipping wait-healthy"
  exit 0
fi

echo "Waiting up to ${TIMEOUT}s for ${SERVICE}..."
deadline=$((SECONDS + TIMEOUT))
while (( SECONDS < deadline )); do
  cid="$(docker compose -f lab/docker-compose.yml ps -q "$SERVICE" 2>/dev/null || true)"
  if [[ -n "$cid" ]]; then
    health="$(docker inspect --format='{{.State.Health.Status}}' "$cid" 2>/dev/null || echo "none")"
    if [[ "$health" == "healthy" ]]; then
      echo "${SERVICE} is healthy"
      exit 0
    fi
    if [[ "$health" == "none" ]]; then
      running="$(docker inspect --format='{{.State.Running}}' "$cid" 2>/dev/null || echo false)"
      if [[ "$running" == "true" ]]; then
        echo "${SERVICE} is running"
        exit 0
      fi
    fi
  fi
  sleep 2
done

echo "Timed out waiting for ${SERVICE}"
exit 1
