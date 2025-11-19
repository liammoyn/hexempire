#!/usr/bin/env bash
set -euo pipefail

# Creates a virtual environment in `.venv` and installs dependencies.
# Works with zsh (macOS default) and bash.

if [ -d ".venv" ]; then
  echo "Using existing .venv virtual environment"
else
  echo "Creating virtual environment in .venv..."
  python3 -m venv .venv
fi

echo "Activating virtual environment and installing requirements..."
source .venv/bin/activate

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "Setup complete. To activate the environment for a session, run:"
echo "  source .venv/bin/activate"
