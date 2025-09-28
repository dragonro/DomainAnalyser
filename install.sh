#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"
REQ_FILE="$BACKEND_DIR/requirements.txt"

if [ ! -d "$BACKEND_DIR" ]; then
  echo "Backend directory not found at $BACKEND_DIR" >&2
  exit 1
fi

if [ ! -f "$REQ_FILE" ]; then
  echo "Requirements file not found at $REQ_FILE" >&2
  exit 1
fi

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install -r "$REQ_FILE"

echo "Environment ready. Activate with: source $VENV_DIR/bin/activate"
