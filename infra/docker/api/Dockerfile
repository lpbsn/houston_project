# syntax=docker/dockerfile:1

FROM python:3.13.13-slim AS python-builder

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.16 --chmod=0755 /uv /usr/local/bin/uv

ARG UV_SYNC_DEV=false

COPY pyproject.toml uv.lock /app/

RUN if [ "$UV_SYNC_DEV" = "true" ]; then \
      uv sync --locked --no-install-project --group dev; \
    else \
      uv sync --locked --no-install-project --no-dev; \
    fi

FROM python:3.13.13-slim AS python-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:/usr/local/bin:${PATH}"

WORKDIR /app

RUN groupadd --gid 1000 houston \
    && useradd --uid 1000 --gid houston --create-home --shell /bin/sh houston

ARG UV_SYNC_DEV=false

COPY --from=python-builder --chown=houston:houston /opt/venv /opt/venv

RUN --mount=type=bind,from=python-builder,source=/usr/local/bin/uv,target=/mnt/uv \
    if [ "$UV_SYNC_DEV" = "true" ]; then install -m 755 /mnt/uv /usr/local/bin/uv; fi

COPY apps/api /app/apps/api
COPY contracts/operational-realtime-invalidation.json /app/contracts/operational-realtime-invalidation.json
COPY infra/docker/api /app/infra/docker/api

WORKDIR /app/apps/api

USER houston
