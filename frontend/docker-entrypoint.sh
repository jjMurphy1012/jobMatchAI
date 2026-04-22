#!/bin/sh
set -e

PORT="${PORT:-8080}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

echo "[entrypoint] PORT=${PORT}"
echo "[entrypoint] BACKEND_URL=${BACKEND_URL}"

sed -e "s|\${PORT}|${PORT}|g" \
    -e "s|\${BACKEND_URL}|${BACKEND_URL}|g" \
    /etc/nginx/templates/default.conf.template \
    > /etc/nginx/conf.d/default.conf

echo "[entrypoint] generated /etc/nginx/conf.d/default.conf:"
cat /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
