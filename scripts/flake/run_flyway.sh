#!/usr/bin/env bash

# This script assumes the following environment variables are set and exported
# by the preceding PostgreSQL setup script (shellhook_postgres.sh):
# - PGHOST
# - PGPORT
# - PGDATABASE
# - PGUSER
# - PGPASSWORD

if [ -z "${PGHOST:-}" ] || [ -z "${PGPORT:-}" ] || [ -z "${PGDATABASE:-}" ] || [ -z "${PGUSER:-}" ] || [ -z "${PGPASSWORD:-}" ]; then
  echo "Error: Required PostgreSQL environment variables (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD) are not set."
  echo "Please ensure shellhook_postgres.sh has run successfully and exported these variables."
  exit 1
fi

echo "Running Flyway migrations..."
flyway \
  -url="jdbc:postgresql://${PGHOST}:${PGPORT}/${PGDATABASE}" \
  -user="${PGUSER}" \
  -password="${PGPASSWORD}" \
  -locations="filesystem:./flyway/sql" \
  migrate

echo "Flyway migrations completed."
