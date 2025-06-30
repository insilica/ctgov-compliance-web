#!/bin/bash
set -e

echo "Starting Flyway migrations..."

# Build Flyway URL from environment variables
if [ -z "${DB_HOST}" ] || [ -z "${DB_PORT}" ] || [ -z "${DB_NAME}" ] || [ -z "${DB_USER}" ] || [ -z "${DB_PASSWORD}" ]; then
  echo "Error: Required database environment variables are not set."
  echo "Required: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD"
  exit 1
fi

# For Cloud SQL Unix socket connections
if [[ "${DB_HOST}" == "/cloudsql/"* ]] && [ -n "${CLOUD_SQL_INSTANCE}" ]; then
  FLYWAY_URL="jdbc:postgresql:///${DB_NAME}?cloudSqlInstance=${CLOUD_SQL_INSTANCE}&socketFactory=com.google.cloud.sql.postgres.SocketFactory"
else
  FLYWAY_URL="jdbc:postgresql://${DB_HOST}:${DB_PORT}/${DB_NAME}"
fi

echo "Running Flyway migrations against: ${FLYWAY_URL}"

flyway \
  -url="${FLYWAY_URL}" \
  -user="${DB_USER}" \
  -password="${DB_PASSWORD}" \
  -locations="filesystem:/flyway/sql" \
  -defaultSchema="public" \
  migrate

echo "Flyway migrations completed successfully."
