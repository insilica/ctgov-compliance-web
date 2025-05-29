#!/usr/bin/env bash

export SKIP_AWS_SECRET_LOADING=false

OLD_OPTS=$(set +o)
set -euo pipefail

source scripts/flake/setup_postgres.sh \
  "postgres" \
  "devpassword" \
  "5433" \
  "toxindex" \
  "localhost" \
  "socket" \
  "/nix/store/3pzlrs5nddszkpgasnrcpf4ifrzm76lb-postgresql-15.13/bin"

source scripts/flake/aws_login.sh

source scripts/flake/run_flyway.sh

source scripts/flake/start_redis.sh

source scripts/load_environment.sh "$AWS_PROFILE" "insilica/toxindex+dev-secret"

eval "$OLD_OPTS"

export FLASK_APP=webserver.app
export FLASK_ENV=development
export DEBUG=1
export PREFERRED_URL_SCHEME=http
export SERVER_NAME=localhost:6513
source .env
export PYTHONPATH="$PWD"