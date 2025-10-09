#!/usr/bin/env bash

source ./pre_run.sh

WORKING_DIR="src/content_publisher" # The app expect to work from within the main directory.

cd "$WORKING_DIR" || (printf "\nCould not change to working dir: %s\n" "$WORKING_DIR" && exit 1)

printf "\nWorking from: %s\n" "$(pwd)"

python3 main.py -p youtube -o portrait \
                  -d /Users/chinomso/Desktop/live-above-3D/aideas-docker-mount/input \
                  -t "Who let the dogs out #shorts"
