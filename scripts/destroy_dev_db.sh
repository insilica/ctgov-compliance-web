#!/usr/bin/env bash
set -euo pipefail

# Script to destroy the development database and clean up stray PostgreSQL processes
echo "WARNING: This will destroy your local development database"
echo "All data will be lost and you'll need to restart your development environment"
echo ""
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Operation cancelled"
    exit 0
fi

# Set PostgreSQL environment variables based on flake.nix
export PGDATA="$PWD/.postgres/data"
export PG_SOCKET_DIR="$PWD/.postgres/socket"
export PGUSER="postgres"
export PGPASSWORD="devpassword"
export PGHOST="localhost"
export PGPORT="5433"
export PGDATABASE="toxindex"

# Check for any running PostgreSQL processes on our port
echo "Checking for PostgreSQL processes on port $PGPORT..."
PG_PIDS=$(lsof -i :$PGPORT -t 2>/dev/null || echo "")

if [ -n "$PG_PIDS" ]; then
    echo "Found PostgreSQL processes running on port $PGPORT. Attempting to terminate them..."
    for PID in $PG_PIDS; do
        echo "Killing process $PID..."
        kill -9 $PID 2>/dev/null || true
    done
    echo "Processes terminated."
else
    echo "No PostgreSQL processes found on port $PGPORT."
fi

# Try stopping PostgreSQL server using pg_ctl if still running
echo "Attempting to stop PostgreSQL server properly..."
if pg_ctl -D "$PGDATA" status > /dev/null 2>&1; then
    pg_ctl -D "$PGDATA" stop -m fast
    echo "PostgreSQL server stopped"
else
    echo "PostgreSQL server not running through pg_ctl"
fi

# Remove PostgreSQL data directory
echo "Removing PostgreSQL data directory..."
if [ -d "$PGDATA" ]; then
    rm -rf "$PGDATA"
    echo "PostgreSQL data directory removed"
else
    echo "No PostgreSQL data directory found"
fi

# Remove PostgreSQL socket directory
echo "Removing PostgreSQL socket directory..."
if [ -d "$PG_SOCKET_DIR" ]; then
    rm -rf "$PG_SOCKET_DIR"
    echo "PostgreSQL socket directory removed"
else
    echo "No PostgreSQL socket directory found"
fi

# Remove PostgreSQL log file
echo "Removing PostgreSQL log file..."
PGLOGFILE="$PWD/.postgres/logfile"
if [ -f "$PGLOGFILE" ]; then
    rm -f "$PGLOGFILE"
    echo "PostgreSQL log file removed"
fi

# Clean up any remaining socket files
echo "Cleaning up any stray socket files..."
find /tmp -name ".s.PGSQL.$PGPORT*" -delete 2>/dev/null || true

echo "Development database and related processes destroyed successfully."
echo "Restart your development environment to create a fresh database."