#!/usr/bin/env bash

source ./pre_run.sh

WORKING_DIR="src/content_publisher" # The app expect to work from within the main directory.

cd "$WORKING_DIR" || (printf "\nCould not change to working dir: %s\n" "$WORKING_DIR" && exit 1)

printf "\nWorking from: %s\n" "$(pwd)"

dir="/Users/chinomso/Desktop/live-above-3D/aideas-docker-mount/input"
title="What Atheists should know about YHWH"

python3 main.py -p tiktok -o portrait -d "$dir" -t "$title"

#python3 main.py -p youtube -o portrait -d "$dir" -t "${title} #shorts" -tg "#YHWH, #God #angelmichael #lucifer, #christianity"
#
#python3 main.py -p youtube,reddit -o landscape -d "$dir" -t title -tg "#YHWH, #God #angelmichael #lucifer, #christianity"



