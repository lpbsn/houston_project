FROM python:3.13.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:/usr/local/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && chmod 755 /usr/local/bin/uv

RUN groupadd --gid 1000 houston \
    && useradd --uid 1000 --gid houston --create-home --shell /bin/sh houston

ARG UV_SYNC_DEV=false

COPY pyproject.toml uv.lock /app/

RUN if [ "$UV_SYNC_DEV" = "true" ]; then \
      uv sync --locked --no-install-project --group dev; \
    else \
      uv sync --locked --no-install-project --no-dev; \
    fi

RUN chown -R houston:houston /opt/venv

COPY apps/api /app/apps/api
COPY contracts/operational-realtime-invalidation.json /app/contracts/operational-realtime-invalidation.json
COPY infra/docker/api /app/infra/docker/api

WORKDIR /app/apps/api

USER houston
