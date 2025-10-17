# app/Dockerfile
FROM python:3.11-slim

LABEL maintainer="docente@example.org"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# instalar utilidades mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    bash \
  && rm -rf /var/lib/apt/lists/*

# crear usuario no-root
RUN useradd --create-home --shell /bin/bash appuser

# usar /app como WORKDIR para coincidir con docker-compose si usas ambos enfoques
WORKDIR /app
USER appuser

# copiar requirements e instalar
COPY --chown=appuser:appuser requirements.txt /app/
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# copiar el codigo de la app
COPY --chown=appuser:appuser . /app

# permisos ejecutables (si se añadieron scripts)
RUN chmod +x /app/entrypoint.sh /app/wait_for_db.py || true

EXPOSE 5000

CMD ["./entrypoint.sh"]

