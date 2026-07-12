#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

CONFIG_DIR="${PYSOAR_CONFIG_DIR:-$ROOT/config}"
LAB_CONFIG="${LAB_CONFIG:-$ROOT/lab/config/lab.yaml}"
if [[ "${LAB_PROFILE:-}" == "full" ]]; then
  LAB_CONFIG="$ROOT/lab/config/full.yaml"
  echo "Using full lab profile configs"
fi
SECRETS_DIR="${PYSOAR_SECRETS_DIR:-$ROOT/secrets}"

mkdir -p "$CONFIG_DIR" "$SECRETS_DIR"

if [[ -f "$LAB_CONFIG" ]]; then
  echo "Installing lab integration configs into $CONFIG_DIR from $LAB_CONFIG"
  ROOT="$ROOT" LAB_CONFIG="$LAB_CONFIG" PYSOAR_CONFIG_DIR="$CONFIG_DIR" python3 - <<'PY'
import os
import yaml
from pathlib import Path

root = Path(os.environ["ROOT"])
config_dir = Path(os.environ["PYSOAR_CONFIG_DIR"])
lab_path = Path(os.environ["LAB_CONFIG"])
lab = yaml.safe_load(lab_path.read_text())
for name, section in lab.items():
    path = config_dir / f"{name}.yaml"
    if not path.exists():
        path.write_text(yaml.safe_dump({name: section}, default_flow_style=False, sort_keys=False))
        print(f"  created {path}")
    else:
        print(f"  kept existing {path}")
PY
fi

if [[ -z "${PYSOAR_MASTER_KEY:-}" && ! -f "$SECRETS_DIR/.master.key" ]]; then
  echo "Initializing secrets master key"
  SECRETS_DIR="$SECRETS_DIR" python3 - <<'PY'
import os
import stat
from pathlib import Path

try:
    from cryptography.fernet import Fernet
except ImportError as exc:
    raise SystemExit(
        "cryptography is required for bootstrap secrets init. "
        "Run: pip install cryptography"
    ) from exc

secrets_dir = Path(os.environ["SECRETS_DIR"])
secrets_dir.mkdir(parents=True, exist_ok=True)
key_path = secrets_dir / ".master.key"
if not key_path.exists():
    key_path.write_bytes(Fernet.generate_key())
    try:
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    print(f"  created {key_path}")
else:
    print(f"  kept existing {key_path}")
PY
fi

echo "Lab bootstrap complete."
