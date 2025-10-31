#!/usr/bin/env bash

source ./pre_run.sh

WORKING_DIR="src/content_publisher" # The app expect to work from within the main directory.

cd "$WORKING_DIR" || (printf "\nCould not change to working dir: %s\n" "$WORKING_DIR" && exit 1)

printf "\nWorking from: %s\n" "$(pwd)"

dir="/Users/chinomso/Desktop/live-above-3D/content-publisher-sample-dir"
title="Faith to convince the Universe"
tags="#pray #faith #speak #conviction #victory #universe #believe"

# X/Twitter
#python3 main.py -p x -o landscape -d "$dir" -t "$title" -tg "$tags"

# TikTok
#python3 main.py -p tiktok -o portrait -d "$dir" -t "$title"

# YouTube shorts
#python3 main.py -p youtube -o portrait -d "$dir" -t "${title} #shorts" -tg "$tags"

# YouTube
#python3 main.py -p youtube,reddit -o landscape -d "$dir" -t title -tg "$tags"



