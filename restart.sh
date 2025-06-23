#!/usr/bin/env bash

# Usage: ./restart.sh [--full|--no-db]
# Default: runs scripts/flake/clean.sh
#   --full   runs scripts/flake/clean_full.sh
#   --no-db  runs scripts/flake/clean_no_db.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEAN_SCRIPT="$SCRIPT_DIR/scripts/flake/clean.sh"

if [[ "$1" == "--full" ]]; then
    CLEAN_SCRIPT="$SCRIPT_DIR/scripts/flake/clean_full.sh"
elif [[ "$1" == "--no-db" ]]; then
    CLEAN_SCRIPT="$SCRIPT_DIR/scripts/flake/clean_no_db.sh"
fi

echo "Running clean script: $CLEAN_SCRIPT"
source "$CLEAN_SCRIPT"

echo -e "\nStarting nix develop..."
nix develop 