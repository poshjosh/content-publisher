#!/usr/bin/env bash

set -euo pipefail

VIRTUAL_ENV_DIR=".venv"

cd ..

if [ ! -d "$VIRTUAL_ENV_DIR" ]; then
  printf "\nCreating virtual environment: %s\n" "$VIRTUAL_ENV_DIR"
  python3 -m venv "$VIRTUAL_ENV_DIR"
fi

printf "\nActivating virtual environment: %s\n" "$VIRTUAL_ENV_DIR"

source "${VIRTUAL_ENV_DIR}/bin/activate"

# We use a specific version, as newer versions have been known to cause issues with pip-compile
python3 -m pip install pip==25.2

# We use a specific version, as newer versions have been known to cause issues with pip-compile
python3 -m pip install pip-tools==7.5.0

printf "\nCompiling dependencies to requirements.txt\n"
pip-compile -o src/content_publisher/requirements.txt pyproject.toml

printf "\nInstalling dependencies from requirements.txt\n"
python3 -m pip install -r src/content_publisher/requirements.txt