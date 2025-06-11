#!/usr/bin/env bash

# List of files and directories to delete
targets=(
  ".postgres"
  ".venv"
  "build"
  "ctgov-compliance-web.egg-info"
  ".aws-profile"
  ".env"
  "blazegraph.jar"
  ".blazegraph.pid"
  "blazegraph.jnl"
  "report.html"
  "report.json"
  "rules.log"
)

# Loop through each target and delete it if it exists
for target in "${targets[@]}"; do
  if [ -e "$target" ]; then
    echo "Deleting: $target"
    rm -rf "$target"
  else
    echo "Not found: $target"
  fi
done

# Find and kill Postgres listening on port 5464
PIDS=$(lsof -t -i :5464 -sTCP:LISTEN -a -c postgres)
PROCESS=$(lsof -i :5464 -sTCP:LISTEN -a -c postgres | head -n 2)
if [ -n "$PIDS" ]; then
  echo "Killing Postgres processes on port 5464 with PID $PIDS: "
  echo "$PROCESS"
  kill $PIDS
else
  echo "No Postgres processes found on port 5464"
fi