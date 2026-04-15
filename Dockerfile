# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm

# Copiamos uv directamente (esto no usa apt-get, así que no fallará)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Saltamos el apt-get update que da error 403
# Solo si realmente necesitas git para un paquete de python, lo habilitamos luego.

ENV UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /workspace

# Instalación de dependencias con uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copiar el entrypoint
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

COPY . .

EXPOSE 8888

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]