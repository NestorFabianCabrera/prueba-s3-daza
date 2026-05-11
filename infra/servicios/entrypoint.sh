#!/bin/sh
set -e

if [ -f /run/secrets/db_pass ] && [ -n "${POSTGRES_USER:-}" ] && [ -n "${POSTGRES_DB:-}" ]; then
    DB_PASS=$(cat /run/secrets/db_pass)
    export POSTGRES_DSN="postgresql://${POSTGRES_USER}:${DB_PASS}@${POSTGRES_HOST:-postgres}:5432/${POSTGRES_DB}"
fi

if [ -f /run/secrets/redis_pass ]; then
    export REDIS_PASSWORD=$(cat /run/secrets/redis_pass)
fi

exec "$@"
