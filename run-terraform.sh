#!/usr/bin/env bash
set -euo pipefail

IMAGE="terraform:v1"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCKER_SOCK="/var/run/docker.sock"
UIDGID="$(id -u):$(id -g)"

# Verificación
if [ ! -S "$DOCKER_SOCK" ]; then
  echo "❌ No se encontró el socket de Docker en $DOCKER_SOCK"
  exit 1
fi

# Si se pasa "shell", abre bash dentro del contenedor
if [ "${1-}" = "shell" ]; then
  shift || true
  docker run --rm -it \
    -u "$UIDGID" \
    -v "${PROJECT_DIR}":/workspace \
    -w /workspace \
    -v "${DOCKER_SOCK}":"${DOCKER_SOCK}" \
    --entrypoint /bin/bash \
    "$IMAGE" "$@"
  exit 0
fi

# Ejecutar terraform normalmente
docker run --rm -it \
  -u "$UIDGID" \
  -v "${PROJECT_DIR}":/workspace \
  -w /workspace \
  -v "${DOCKER_SOCK}":"${DOCKER_SOCK}" \
  "$IMAGE" "$@"


