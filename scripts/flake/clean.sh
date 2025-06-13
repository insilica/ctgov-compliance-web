#!/usr/bin/env bash

# List of files and directories to delete
targets=(
  ".postgres"
  ".venv"
  "build"
  "ctgov_compliance_web.egg-info"
  ".env"
  "blazegraph.jar"
  ".blazegraph.pid"
  "blazegraph.jnl"
  "report.html"
  "report.json"
  "rules.log"
)

# Function to safely delete a target
delete_target() {
  local target=$1
  if [ -e "$target" ]; then
    echo "Deleting: $target"
    if ! rm -rf "$target" 2>/dev/null; then
      echo "Permission denied, trying with sudo..."
      rm -rf "$target"
    fi
  else
    echo "Not found: $target"
  fi
}

# Loop through each target and delete it
for target in "${targets[@]}"; do
  delete_target "$target"
done

# Find and kill Postgres listening on port 5464
PIDS=$(lsof -t -i :5464 -sTCP:LISTEN -a -c postgres)
PROCESS=$(lsof -i :5464 -sTCP:LISTEN -a -c postgres | head -n 2)
if [ -n "$PIDS" ]; then
  echo "Killing Postgres processes on port 5464 with PID $PIDS: "
  echo "$PROCESS"
  kill $PIDS
  for pid in $PIDS; do
    while kill -0 $pid 2>/dev/null; do
      echo "Waiting for Postgres process $pid to terminate..."
      sleep 1
    done
  done
else
  echo "No Postgres processes found on port 5464"
fi

# Find and kill Java process listening on port 9999
JAVA_PIDS=$(lsof -t -i :9999 -sTCP:LISTEN -a -c java)
JAVA_PROCESS=$(lsof -i :9999 -sTCP:LISTEN -a -c java | head -n 2)
if [ -n "$JAVA_PIDS" ]; then
  echo "Killing Java processes on port 9999 with PID $JAVA_PIDS:"
  echo -e "Full entry info:\n$JAVA_PROCESS"
  kill $JAVA_PIDS
  for pid in $JAVA_PIDS; do
    while kill -0 $pid 2>/dev/null; do
      echo "Waiting for Java process $pid to terminate..."
      sleep 1
    done
  done
else
  echo "No Java processes found on port 9999"
fi