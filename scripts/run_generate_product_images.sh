#!/usr/bin/env bash
# Run generate_product_images.py using a project venv (avoids Homebrew
# "externally-managed-environment" when system Python blocks pip install).
# Usage: ./scripts/run_generate_product_images.sh   (from repo root)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

cd "$PROJECT_ROOT"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment at .venv ..."
  python3 -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -c "from PIL import Image" 2>/dev/null; then
  echo "Installing Pillow into .venv ..."
  "$VENV_DIR/bin/pip" install -q Pillow
fi

"$VENV_DIR/bin/python" "$SCRIPT_DIR/generate_product_images.py" "$@"
