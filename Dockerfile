# Imagen de desarrollo: Jupyter Lab + dependencias del curso (uv + uv.lock).
# syntax=docker/dockerfile:1

FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

COPY . .

EXPOSE 8888

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
