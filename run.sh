#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"
REQ_FILE="$BACKEND_DIR/requirements.txt"
PYTHON_BIN=${PYTHON_BIN:-python3}

if [ ! -d "$BACKEND_DIR" ]; then
  echo "Backend directory not found at $BACKEND_DIR" >&2
  exit 1
fi

if [ ! -f "$REQ_FILE" ]; then
  echo "Requirements file not found at $REQ_FILE" >&2
  exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python interpreter '$PYTHON_BIN' not found." >&2
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  VENV_CREATED=true
else
  VENV_CREATED=false
fi

source "$VENV_DIR/bin/activate"

if [ "$VENV_CREATED" = true ] || [ "$REQ_FILE" -nt "$VENV_DIR/.requirements_timestamp" ]; then
  echo "Installing dependencies from $REQ_FILE"
  pip install --upgrade pip
  pip install -r "$REQ_FILE"
  touch "$VENV_DIR/.requirements_timestamp"
fi

cd "$BACKEND_DIR"
echo "Starting Domain Analyzer API on http://0.0.0.0:3000"
exec uvicorn app.main:app --host 0.0.0.0 --port 3000
