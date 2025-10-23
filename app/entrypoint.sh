#!/usr/bin/env bash
set -e

echo "=== Iniciando entrypoint ==="
echo "Variables de entorno:"
echo "MYSQL_HOST: $MYSQL_HOST"
echo "MYSQL_PORT: $MYSQL_PORT"
echo "MYSQL_USER: $MYSQL_USER"
echo "MYSQL_DATABASE: $MYSQL_DATABASE"


: "${MYSQL_HOST:=mysql}"
: "${MYSQL_PORT:=3306}"
: "${MYSQL_USER:=appuser}"
: "${MYSQL_PASSWORD:=apppassword}"
: "${MYSQL_DATABASE:=appdb}"
: "${WAIT_TIMEOUT:=30}"

echo "Esperando a MySQL en ${MYSQL_HOST}:${MYSQL_PORT} (timeout ${WAIT_TIMEOUT}s)..."

if ! python wait_for_db.py \
  --host "$MYSQL_HOST" --port "$MYSQL_PORT" \
  --user "$MYSQL_USER" --password "$MYSQL_PASSWORD" \
  --database "$MYSQL_DATABASE" --timeout "$WAIT_TIMEOUT"; then
  echo "ERROR: No se pudo conectar a MySQL"
  exit 1
fi

echo "MySQL disponible. Iniciando Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --access-logfile - app:app

