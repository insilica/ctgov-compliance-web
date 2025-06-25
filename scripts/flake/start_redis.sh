#!/usr/bin/env bash

# Redis is not used by the application - stubbed out
echo "Redis startup skipped (not used by application)"
exit 0

if ! pgrep redis-server > /dev/null; then
  echo "Starting Redis server..."
  redis-server --daemonize yes > /dev/null
else
  echo "Redis is already running."
fi
