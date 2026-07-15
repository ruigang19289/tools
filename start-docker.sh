#!/bin/sh
# Tools 项目启动脚本 (Docker版)

set -eu

mkdir -p /app/logs /app/data /app/data/cache /app/data/vdbench-result /run/nginx

if [ ! -f /app/data/db.sqlite3 ]; then
  : > /app/data/db.sqlite3
fi

python3 manage.py migrate --noinput >/app/logs/migrate.log 2>&1

daphne -b 0.0.0.0 -p 6000 backend.asgi:application >/app/logs/django.log 2>&1 &
DJANGO_PID=$!

cp /app/nginx.conf /etc/nginx/http.d/default.conf
nginx -t >/app/logs/nginx-test.log 2>&1

cleanup() {
  if kill -0 "$DJANGO_PID" 2>/dev/null; then
    kill "$DJANGO_PID" 2>/dev/null || true
    wait "$DJANGO_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

exec nginx -g 'daemon off;'
