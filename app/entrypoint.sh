#!/usr/bin/env bash
set -e

: "${MYSQL_HOST:=mysql}"
: "${MYSQL_PORT:=3306}"
: "${MYSQL_USER:=appuser}"
: "${MYSQL_PASSWORD:=apppassword}"
: "${MYSQL_DATABASE:=appdb}"
: "${WAIT_TIMEOUT:=30}"

echo "Esperando a MySQL en ${MYSQL_HOST}:${MYSQL_PORT} (timeout ${WAIT_TIMEOUT}s)..."
python wait_for_db.py \
  --host "$MYSQL_HOST" --port "$MYSQL_PORT" \
  --user "$MYSQL_USER" --password "$MYSQL_PASSWORD" \
  --database "$MYSQL_DATABASE" --timeout "$WAIT_TIMEOUT"

echo "Arrancando Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 app:app

