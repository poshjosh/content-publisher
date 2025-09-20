#!/usr/bin/env bash

ENV_FILE="${ENV_FILE:-.env}"

printf "\nEnvironment file: %s\n" "$ENV_FILE"

cd .. && source .venv/bin/activate || exit 1

printf "\nExporting environment\n"

set -a
# shellcheck source=.env
source "$ENV_FILE"
set +a

export PYTHONUNBUFFERED=1
