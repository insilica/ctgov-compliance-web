#!/usr/bin/env bash

export SKIP_AWS_SECRET_LOADING=false

OLD_OPTS=$(set +o)
set -euo pipefail

source scripts/flake/setup_postgres.sh \
  "postgres" \
  "devpassword" \
  "5464" \
  "ctgov-web" \
  "localhost" \
  "socket" \
  "/nix/store/3pzlrs5nddszkpgasnrcpf4ifrzm76lb-postgresql-15.13/bin"

source scripts/flake/aws_login.sh

source scripts/flake/run_flyway.sh

source scripts/flake/start_redis.sh

source scripts/flake/start_blazegraph.sh

source scripts/load_environment.sh "$AWS_PROFILE" "ctgov-compliance-web-dev"

eval "$OLD_OPTS"

export FLASK_APP=web.app
export FLASK_ENV=development
export DEBUG=1
export PREFERRED_URL_SCHEME=http
export SERVER_NAME=localhost:6513
source .env
export PYTHONPATH="$PWD"

# Only populate mock data if the organization table is empty
ORG_COUNT=$(PGPASSWORD=devpassword psql -h localhost -p 5464 -U postgres -d ctgov-web -tAc "SELECT COUNT(*) FROM organization;" 2>/dev/null || echo 0)
if [ "$ORG_COUNT" -eq 0 ]; then
  echo "Populating mock data (organization table is empty)"
  uv run scripts/init_mock_data.py --orgs 1000 --users 100 --trials 100000 --skip-blazegraph
else
  echo "Skipping mock data population (organization table already populated)"
fi