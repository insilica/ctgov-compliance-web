#!/usr/bin/env bash

# Starts a local Blazegraph instance from a jar if not already running.
# If the jar is missing it will be downloaded automatically.
# Blazegraph will listen on port 9999 by default.

set -euo pipefail

JAR_PATH="${BLAZEGRAPH_JAR:-$PWD/blazegraph.jar}"
echo $PWD
PORT="${BLAZEGRAPH_PORT:-9999}"
DOWNLOAD_URL="https://github.com/blazegraph/database/releases/download/BLAZEGRAPH_RELEASE_2_1_5/blazegraph.jar"

if lsof -i:"$PORT" >/dev/null 2>&1; then
    echo "Blazegraph already running on port $PORT."
fi

if [ ! -f "$JAR_PATH" ]; then
    echo "Downloading Blazegraph jar to $JAR_PATH..."
    curl -L -o "$JAR_PATH" "$DOWNLOAD_URL"
fi

if ! lsof -i:"$PORT" >/dev/null 2>&1; then
    echo "Starting Blazegraph on port $PORT..."
    java -Djetty.port="$PORT" -jar "$JAR_PATH" >/dev/null 2>&1 &
    echo $! > .blazegraph.pid
    echo "Blazegraph started with PID $(cat .blazegraph.pid)"
fi