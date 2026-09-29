from __future__ import annotations

from pathlib import Path

from config.celery import app
from config.celery_routing import (
    QUEUE_AI_BACKGROUND,
    QUEUE_AI_INTERACTIVE,
    WORKER_QUEUES,
)
from django.conf import settings

REPO_ROOT = Path(__file__).resolve().parents[5]


def test_every_houston_task_is_explicitly_routed():
    app.loader.import_default_modules()
    missing = sorted(
        name
        for name in app.tasks
        if name.startswith("houston.") and name not in settings.CELERY_TASK_ROUTES
    )
    assert missing == []


def test_interactive_and_background_workers_do_not_share_queues():
    assert QUEUE_AI_INTERACTIVE not in WORKER_QUEUES["background"]
    assert QUEUE_AI_BACKGROUND not in WORKER_QUEUES["ai_interactive"]


def test_local_and_railway_run_three_worker_pools_without_redis_broker():
    compose = (REPO_ROOT / "docker-compose.yml").read_text()
    assert "celery-ai-interactive:" in compose
    assert "celery-operational:" in compose
    assert "celery-background:" in compose
    assert "amqp://houston:houston@rabbitmq:5672//" in compose
    assert "CELERY_RESULT_BACKEND" not in compose
    assert "-Q ai_interactive" in compose
    assert "--prefetch-multiplier=1" in compose
    assert "-Q operational" in compose
    assert "-Q ai_background,maintenance" in compose

    interactive = (
        REPO_ROOT / "infra/railway/celery-ai-interactive/railway.toml"
    ).read_text()
    operational = (REPO_ROOT / "infra/railway/celery-operational/railway.toml").read_text()
    background = (REPO_ROOT / "infra/railway/celery-background/railway.toml").read_text()
    assert "-Q ai_interactive" in interactive
    assert "--prefetch-multiplier=1" in interactive
    assert "-Q operational" in operational
    assert "ai_background" not in operational
    assert "-Q ai_background,maintenance" in background
    assert "CELERY_RESULT_BACKEND" not in (
        REPO_ROOT / "apps/api/config/settings.py"
    ).read_text()
    assert not (REPO_ROOT / "infra/railway/celery-worker/railway.toml").exists()
