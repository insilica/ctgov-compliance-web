#!/usr/bin/env bash

# Arguments:
#   1 - PostgreSQL user
#   2 - PostgreSQL password
#   3 - PostgreSQL port
#   4 - Database name
#   5 - Host
#   6 - Socket directory subpath
#   7 - PostgreSQL bin path

PG_SETTINGS_USER="$1"
PG_SETTINGS_PASSWORD="$2"
PG_SETTINGS_PORT="$3"
PG_SETTINGS_DB_NAME="$4"
PG_SETTINGS_HOST="$5"
PG_SETTINGS_SOCKET_DIR_SUBPATH="$6"
POSTGRESQL_BIN_PATH="$7"

export PG_SETTINGS_USER PG_SETTINGS_PASSWORD PG_SETTINGS_PORT \
       PG_SETTINGS_DB_NAME PG_SETTINGS_HOST PG_SETTINGS_SOCKET_DIR_SUBPATH \
       POSTGRESQL_BIN_PATH

# Call the existing PostgreSQL helper
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/.."

#!/usr/bin/env bash
set -euo pipefail

# This script assumes the following environment variables are set by the caller (e.g., flake.nix shellHook):
# - PG_SETTINGS_USER
# - PG_SETTINGS_PASSWORD
# - PG_SETTINGS_PORT
# - PG_SETTINGS_DB_NAME
# - PG_SETTINGS_HOST
# - PG_SETTINGS_SOCKET_DIR_SUBPATH
# - POSTGRESQL_BIN_PATH (e.g., ${pkgs.postgresql_15}/bin)

echo "Setting up PostgreSQL development environment..."

# Export standard PostgreSQL environment variables
export PGUSER="${PG_SETTINGS_USER}"
export PGPASSWORD="${PG_SETTINGS_PASSWORD}"
export PGHOST="${PG_SETTINGS_HOST}" # For clients to default to TCP/IP
export PGPORT="${PG_SETTINGS_PORT}"
export PGDATABASE="${PG_SETTINGS_DB_NAME}"

export PGDATA="$PWD/.postgres/data"
export PG_SOCKET_DIR="$PWD/.postgres/${PG_SETTINGS_SOCKET_DIR_SUBPATH}" # Explicit socket directory for the server
export PATH="${POSTGRESQL_BIN_PATH}:$PATH"

PGLOGFILE="$PWD/.postgres/logfile"

mkdir -p "$PWD/.postgres" # Ensure .postgres parent directory exists
mkdir -p "$PG_SOCKET_DIR"  # Ensure the socket directory exists before initdb/start

if [ ! -d "$PGDATA" ] || [ ! -f "$PGDATA/postgresql.conf" ]; then
  echo "Initializing new PostgreSQL instance in $PGDATA..."
  # initdb creates PGDATA, so ensure its parent exists.
  # If PGDATA exists but is empty or incomplete, initdb might fail or behave unexpectedly.
  # Consider rm -rf "$PGDATA" if you want a truly fresh initdb, but be cautious.
  mkdir -p "$PGDATA" # Ensure PGDATA directory itself exists if it's just a path
  rm -rf "${PGDATA:?}"/* # Clean out PGDATA before initdb if it exists but is not properly initialized.
                        # The :? ensures PGDATA is set and not empty, preventing "rm -rf /*".

  initdb --username="$PGUSER" --pwfile=<(echo "$PGPASSWORD") -D "$PGDATA"

  echo "Configuring PostgreSQL..."
  echo "listen_addresses = '${PG_SETTINGS_HOST}'" >> "$PGDATA/postgresql.conf"
  echo "port = ${PG_SETTINGS_PORT}" >> "$PGDATA/postgresql.conf"
  echo "unix_socket_directories = '$PG_SOCKET_DIR'" >> "$PGDATA/postgresql.conf"
  # Add any other necessary configurations here
fi

if ! pg_ctl -D "$PGDATA" status > /dev/null 2>&1; then
  echo "Starting PostgreSQL server (Log: $PGLOGFILE)..."
  # Ensure log file directory exists if PGLOGFILE path includes subdirectories
  mkdir -p "$(dirname "$PGLOGFILE")"
  if ! pg_ctl -D "$PGDATA" -l "$PGLOGFILE" -w -t 30 start; then
    echo "--------------------------------------------------------------------"
    echo "PostgreSQL FAILED to start. Contents of $PGLOGFILE:"
    cat "$PGLOGFILE"
    echo "--------------------------------------------------------------------"
    echo "Exiting due to PostgreSQL startup failure."
    exit 1
  fi
  echo "PostgreSQL server started successfully."
else
  echo "PostgreSQL already running."
fi

# Create database if it doesn't exist
# psql will use PGHOST, PGPORT etc. for TCP/IP connection
if ! psql -lqt | cut -d \| -f 1 | grep -qw "${PGDATABASE}"; then
  echo "Creating database: ${PGDATABASE}..."
  createdb "${PGDATABASE}"
else
  echo "Database ${PGDATABASE} already exists."
fi

echo "PostgreSQL environment variables exported:"
echo "  PGUSER=$PGUSER"
echo "  PGHOST=$PGHOST"
echo "  PGPORT=$PGPORT"
echo "  PGDATABASE=$PGDATABASE"
echo "  PG_SOCKET_DIR=$PG_SOCKET_DIR"
echo "PostgreSQL is accessible on: ${PGHOST}:${PGPORT} (TCP/IP)"
echo "PostgreSQL server socket directory: $PG_SOCKET_DIR"
echo "Database: ${PGDATABASE}, User: ${PGUSER}"
