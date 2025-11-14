#!/usr/bin/env bash

source ./pre_run.sh

WORKING_DIR="src/content_publisher" # The app expect to work from within the main directory.

cd "$WORKING_DIR" || (printf "\nCould not change to working dir: %s\n" "$WORKING_DIR" && exit 1)

printf "\nWorking from: %s\n" "$(pwd)"

platforms="tiktok"
orientation="portrait"
dir="/Users/chinomso/Desktop/live-above-3D/content-publisher-sample-dir"
title="Stand by your words, even when they fail"
tags="#pray,#faith,#speak,#conviction,#victory,#universe,#believe"

python3 main.py -v true -p "$platforms" -o "$orientation" -d "$dir" -t "$title" -tg "$tags"

