#!/usr/bin/env bash
set -euo pipefail

# create python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start services with docker-compose
if [ ! "$(docker ps -q -f name=web_postgres)" ]; then
    docker compose -f "$(dirname "$0")/../docker-compose.yml" up -d postgres blazegraph
fi

# Apply Django migrations
(cd ctgovapp && python manage.py migrate --noinput)

# Populate blazegraph with mock data
python scripts/populate_blazegraph.py

echo "Setup complete"
