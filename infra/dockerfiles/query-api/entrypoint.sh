#!/bin/sh
set -e
[ -f /run/secrets/redis_password ] && export REDIS_PASSWORD=$(cat /run/secrets/redis_password)
if [ -f /run/secrets/pg_password ]; then
  export POSTGRES_DSN="postgresql://${POSTGRES_USER}:$(cat /run/secrets/pg_password)@${POSTGRES_HOST:-postgres}:5432/${POSTGRES_DB}"
fi
exec "$@"
