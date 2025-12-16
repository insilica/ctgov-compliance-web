#!/usr/bin/env bash
set -euo pipefail
export FLASK_APP=web.app
export FLASK_ENV=${FLASK_ENV:-development}
flask run "$@"
