#!/usr/bin/env bash
# Seed a live MISP instance with test indicators (requires PyMISP and reachable MISP).
set -euo pipefail

export MISP_URL="${MISP_URL:-https://localhost}"
export MISP_KEY="${MISP_API_KEY:-${MISP_KEY:-}}"
export MISP_VERIFY="${MISP_VERIFY:-false}"

if [[ -z "$MISP_KEY" ]]; then
  echo "Set MISP_API_KEY or MISP_KEY to seed MISP."
  exit 1
fi

python3 - <<PY
import os
import sys

try:
    from pymisp import MISPEvent, MISPAttribute, PyMISP
except ImportError:
    print("PyMISP required: pip install pymisp", file=sys.stderr)
    sys.exit(1)

url = os.environ["MISP_URL"]
key = os.environ["MISP_KEY"]
verify = os.environ.get("MISP_VERIFY", "false").lower() in ("1", "true", "yes")

misp = PyMISP(url, key, ssl=url.startswith("https"), verifycert=verify)
event = MISPEvent()
event.info = "PySOAR lab seed event"
event.distribution = 0
event.threat_level_id = 2
for ip in ("203.0.113.10", "203.0.113.20", "198.51.100.5"):
    event.add_attribute("ip-dst", ip)
result = misp.add_event(event)
print("Seeded MISP event:", result.get("Event", {}).get("id", result))
PY

echo "MISP seed complete."
