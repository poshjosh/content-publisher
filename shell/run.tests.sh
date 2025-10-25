#!/usr/bin/env bash

# shellcheck disable=SC2034
ENV_FILE=".env.test"
source ./pre_run.sh

WORKING_DIR="src"

cd "$WORKING_DIR" || (printf "\nCould not change to working dir: %s\n" "$WORKING_DIR" && exit 1)

printf "\nWorking from: %s\n" "$(pwd)"

printf "\nStarting tests\n\n"

python3 -m unittest discover -s test/app -p "*test.py"