#!/usr/bin/env bash

source ./pre_run.sh

WORKING_DIR="src/main" # The app expect to work from within the main directory.

cd "$WORKING_DIR" || (printf "\nCould not change to working dir: %s\n" "$WORKING_DIR" && exit 1)

printf "\nWorking from: %s\n" "$(pwd)"

python3 main.py
