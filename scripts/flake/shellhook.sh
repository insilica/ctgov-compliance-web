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

# populate mock data
python scripts/init_mock_data.py