#!/bin/sh
set -e

: "${PORT:=80}"
: "${BACKEND_URL:=http://localhost:8000}"

# Replace environment variables in nginx config
envsubst '${PORT} ${BACKEND_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Start nginx
exec nginx -g 'daemon off;'
