#!/usr/bin/env bash


OLD_OPTS=$(set +o)
set -euo pipefail

# Skip PostgreSQL setup in CI environment
if [ "${SKIP_POSTGRES_SETUP:-false}" != "true" ]; then
  echo "Setting up PostgreSQL..."
  source scripts/flake/setup_postgres.sh \
    "postgres" \
    "devpassword" \
    "5464" \
    "ctgov-web" \
    "localhost" \
    "socket" \
    "/nix/store/3pzlrs5nddszkpgasnrcpf4ifrzm76lb-postgresql-15.13/bin"
else
  echo "Skipping PostgreSQL setup (CI environment)"
  # Set required environment variables for CI
  export PGUSER="postgres"
  export PGPASSWORD="devpassword"
  export PGHOST="localhost"
  export PGPORT="5464"
  export PGDATABASE="ctgov-web"
fi


# Skip Flyway in CI environment (assuming no migrations needed for tests)
if [ "${SKIP_POSTGRES_SETUP:-false}" != "true" ] && [ "${SKIP_FLYWAY_SETUP:-false}" != "true" ]; then
  source scripts/flake/run_flyway.sh
else
  echo "Skipping Flyway (CI environment)"
fi




eval "$OLD_OPTS"

export FLASK_APP=web.app
export FLASK_ENV=development
export DEBUG=1
export PREFERRED_URL_SCHEME=http
export SERVER_NAME=localhost:6513

# Source .env file if it exists (skip in CI)
if [ -f .env ] && [ "${CI:-false}" != "true" ]; then
  source .env
fi

export PYTHONPATH="$PWD"

# Skip mock data population in CI environment
if [ "${CI:-false}" != "true" ]; then
  # Only populate mock data if the organization table is empty
  ORG_COUNT=$(psql -tAc "SELECT COUNT(*) FROM organization;" 2>/dev/null || echo 0)
  if [ "$ORG_COUNT" -eq 0 ]; then
    echo "Populating mock data (organization table is empty)"
    uv run scripts/init_mock_data.py --orgs 1000 --users 100 --trials 10000
  else
    echo "Skipping mock data population (organization table already populated)"
  fi
else
  echo "Skipping mock data population (CI environment)"
fi