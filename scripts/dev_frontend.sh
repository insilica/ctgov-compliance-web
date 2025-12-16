#!/usr/bin/env bash
set -euo pipefail
FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../web/frontend" && pwd)"
if [[ ! -f "${FRONTEND_DIR}/package.json" ]]; then
  cat <<'MSG'
[frontend] No package.json detected yet.
Create one (e.g., via `npm create vite@latest`) and rerun this script to start the React dev server.
MSG
  exit 0
fi
cd "${FRONTEND_DIR}"
npm install
npm run dev
