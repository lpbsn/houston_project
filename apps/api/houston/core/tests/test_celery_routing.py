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


def test_recovery_thresholds_stay_at_or_above_hard_time_limits():
    assert settings.HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS >= (
        settings.HOUSTON_CELERY_OBSERVATION_PIPELINE_TIME_LIMIT_SECONDS
    )
    assert settings.HOUSTON_ANALYTICS_PATTERN_PROCESSING_STALE_SECONDS >= (
        settings.HOUSTON_CELERY_ANALYTICS_PATTERN_TIME_LIMIT_SECONDS
    )


def test_rabbitmq4_temporary_queues_are_exclusive_and_remote_control_is_off():
    assert settings.CELERY_WORKER_ENABLE_REMOTE_CONTROL is False
    assert settings.CELERY_CONTROL_QUEUE_EXCLUSIVE is True
    assert settings.CELERY_EVENT_QUEUE_EXCLUSIVE is True
    assert app.conf.worker_enable_remote_control is False
    assert app.conf.control_queue_exclusive is True
    assert app.conf.control_queue_durable is False
    assert app.conf.event_queue_exclusive is True
    assert app.conf.event_queue_durable is False
    mailbox = app.control.mailbox
    assert mailbox.queue_exclusive is True
    assert mailbox.queue_durable is False


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
    assert "brain_analysis" not in WORKER_QUEUES["ai_interactive"]
    assert "brain_analysis" not in WORKER_QUEUES["operational"]
    assert "brain_analysis" not in WORKER_QUEUES["background"]
    assert QUEUE_AI_INTERACTIVE not in WORKER_QUEUES["brain"]
    assert "operational" not in WORKER_QUEUES["brain"]
    assert "ai_background" not in WORKER_QUEUES["brain"]
    assert "maintenance" not in WORKER_QUEUES["brain"]
    routes = settings.CELERY_TASK_ROUTES
    assert routes["houston.signals.tasks.process_observation_task"]["queue"] == "ai_interactive"
    assert routes["houston.brain.tasks.run_brain_analysis_task"]["queue"] == "brain_analysis"
    assert routes["houston.brain.tasks.recover_brain_analysis_task"]["queue"] == "operational"


def test_local_and_railway_run_worker_pools_without_redis_broker():
    compose = (REPO_ROOT / "docker-compose.yml").read_text()
    assert "celery-ai-interactive:" in compose
    assert "celery-operational:" in compose
    assert "celery-background:" in compose
    assert "celery-brain:" in compose
    assert "amqp://houston:houston@rabbitmq:5672//" in compose
    assert "CELERY_RESULT_BACKEND" not in compose
    assert "-Q ai_interactive" in compose
    assert "--prefetch-multiplier=1" in compose
    assert "--without-mingle" not in compose
    assert "-Q operational" in compose
    assert "-Q ai_background,maintenance" in compose
    assert "-Q brain_analysis" in compose
    brain = compose.split("celery-brain:", 1)[1].split("celery-beat:", 1)[0]
    assert "-Q brain_analysis" in brain
    assert "--prefetch-multiplier=1" in brain
    assert "ai_interactive" not in brain
    for pool in ("celery-ai-interactive:", "celery-operational:", "celery-background:"):
        block = compose.split(pool, 1)[1].split("\n  celery-", 1)[0]
        assert "brain_analysis" not in block
    assert "CELERY_AI_INTERACTIVE_CONCURRENCY:-2" in compose
    assert "CELERY_OPERATIONAL_CONCURRENCY:-1" in compose
    assert "CELERY_BACKGROUND_CONCURRENCY:-1" in compose
    assert "CELERY_BRAIN_CONCURRENCY:-2" in compose
    assert "CELERY_WORKER_CONCURRENCY:-4" not in compose

    interactive = (
        REPO_ROOT / "infra/railway/celery-ai-interactive/railway.toml"
    ).read_text()
    operational = (REPO_ROOT / "infra/railway/celery-operational/railway.toml").read_text()
    background = (REPO_ROOT / "infra/railway/celery-background/railway.toml").read_text()
    brain_railway = (REPO_ROOT / "infra/railway/celery-brain/railway.toml").read_text()
    assert "-Q ai_interactive" in interactive
    assert "--prefetch-multiplier=1" in interactive
    assert "brain_analysis" not in interactive
    assert "-Q operational" in operational
    assert "ai_background" not in operational
    assert "brain_analysis" not in operational
    assert "-Q ai_background,maintenance" in background
    assert "brain_analysis" not in background
    assert "-Q brain_analysis" in brain_railway
    assert "--prefetch-multiplier=1" in brain_railway
    assert "ai_interactive" not in brain_railway
    assert "CELERY_RESULT_BACKEND" not in (
        REPO_ROOT / "apps/api/config/settings.py"
    ).read_text()
    assert not (REPO_ROOT / "infra/railway/celery-worker/railway.toml").exists()
    contract = (REPO_ROOT / "docs/deploy/railway_deploy_contract.md").read_text()
    assert "houston-worker@%h" not in contract
    for relative in (
        "infra/railway/celery-ai-interactive/railway.toml",
        "infra/railway/celery-operational/railway.toml",
        "infra/railway/celery-background/railway.toml",
        "infra/railway/celery-brain/railway.toml",
    ):
        start_command = next(
            line
            for line in (REPO_ROOT / relative).read_text().splitlines()
            if line.startswith("startCommand")
        )
        assert "--without-mingle" not in start_command
        assert start_command in contract
