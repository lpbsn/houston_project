import os
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent


def env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(int(default))).lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str) -> list[str]:
    value = env_str(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def env_int(name: str, default: int) -> int:
    return int(env_str(name, str(default)))


SECRET_KEY = env_str("DJANGO_SECRET_KEY", "replace-me-for-local-dev")
DEBUG = env_bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "channels",
    "houston.core",
    "houston.accounts",
    "houston.organizations",
    "houston.establishments",
    "houston.observations",
    "houston.signals",
    "houston.actions",
    "houston.checklists",
    "houston.comments",
    "houston.notifications",
    "houston.realtime",
    "houston.chat",
    "houston.ai",
    "houston.events",
    "houston.uploads",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

_postgres_sslmode = env_str("POSTGRES_SSLMODE", "")
_postgres_db_options: dict[str, str] = {}
if _postgres_sslmode:
    _postgres_db_options["sslmode"] = _postgres_sslmode

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_str("POSTGRES_DB", "houston"),
        "USER": env_str("POSTGRES_USER", "houston"),
        "PASSWORD": env_str("POSTGRES_PASSWORD", "houston"),
        "HOST": env_str("POSTGRES_HOST", "postgres"),
        "PORT": env_str("POSTGRES_PORT", "5432"),
        **({"OPTIONS": _postgres_db_options} if _postgres_db_options else {}),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

HOUSTON_PRIVATE_MEDIA_ROOT = env_str(
    "HOUSTON_PRIVATE_MEDIA_ROOT",
    str(BASE_DIR / "private_media"),
)
HOUSTON_TEMPORARY_UPLOAD_TTL_HOURS = env_int("HOUSTON_TEMPORARY_UPLOAD_TTL_HOURS", 24)
HOUSTON_OBSERVATION_MEDIA_PREVIEW_TTL_SECONDS = env_int(
    "HOUSTON_OBSERVATION_MEDIA_PREVIEW_TTL_SECONDS",
    3600,
)
HOUSTON_OBSERVATION_PHOTO_MAX_BYTES = env_int(
    "HOUSTON_OBSERVATION_PHOTO_MAX_BYTES",
    10 * 1024 * 1024,
)
HOUSTON_TRANSCRIPTION_AUDIO_MAX_BYTES = env_int(
    "HOUSTON_TRANSCRIPTION_AUDIO_MAX_BYTES",
    10 * 1024 * 1024,
)
HOUSTON_AI_TRANSCRIPTION_MODEL = env_str(
    "HOUSTON_AI_TRANSCRIPTION_MODEL",
    "gpt-4o-transcribe",
)
HOUSTON_AI_TRANSCRIPTION_TIMEOUT_SECONDS = env_int(
    "HOUSTON_AI_TRANSCRIPTION_TIMEOUT_SECONDS",
    10,
)
HOUSTON_AI_TRANSCRIPTION_PROMPT_VERSION = env_str(
    "HOUSTON_AI_TRANSCRIPTION_PROMPT_VERSION",
    "ai_transcription_v1",
)
HOUSTON_AI_TRANSCRIPTION_PROVIDER = env_str(
    "HOUSTON_AI_TRANSCRIPTION_PROVIDER",
    "openai",
)
HOUSTON_AI_OBSERVATION_PROVIDER = env_str(
    "HOUSTON_AI_OBSERVATION_PROVIDER",
    "openai",
)
HOUSTON_AI_OBSERVATION_MODEL = env_str(
    "HOUSTON_AI_OBSERVATION_MODEL",
    "gpt-4.1-mini",
)
HOUSTON_AI_OBSERVATION_TIMEOUT_SECONDS = env_int(
    "HOUSTON_AI_OBSERVATION_TIMEOUT_SECONDS",
    30,
)
HOUSTON_AI_OBSERVATION_MAX_RETRIES = env_int("HOUSTON_AI_OBSERVATION_MAX_RETRIES", 2)
AUTH_USER_MODEL = "accounts.User"

REDIS_URL = env_str("REDIS_URL", "redis://redis:6379/0")
CELERY_BROKER_URL = env_str("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = env_str("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

# Celery Beat (first scheduled job in Houston). Requires a `celery-beat` process;
# lazy checklist materialization on execution-feed read remains the primary safety net.
CELERY_BEAT_SCHEDULE = {
    "materialize-checklist-assignments-horizon": {
        "task": "houston.checklists.tasks.materialize_checklist_assignments_horizon_task",
        "schedule": crontab(
            hour=env_int("HOUSTON_CHECKLIST_HORIZON_BEAT_HOUR_UTC", 3),
            minute=env_int("HOUSTON_CHECKLIST_HORIZON_BEAT_MINUTE_UTC", 0),
        ),
        "kwargs": {"establishment_id": None},
    },
    "purge-chat-messages": {
        "task": "houston.chat.tasks.purge_chat_messages_task",
        "schedule": crontab(
            hour=env_int("HOUSTON_CHAT_PURGE_BEAT_HOUR_UTC", 4),
            minute=env_int("HOUSTON_CHAT_PURGE_BEAT_MINUTE_UTC", 0),
        ),
        "kwargs": {"establishment_id": None},
    },
    "cleanup-expired-uploads": {
        "task": "houston.uploads.tasks.cleanup_expired_uploads_task",
        "schedule": crontab(
            hour=env_int("HOUSTON_UPLOAD_PURGE_BEAT_HOUR_UTC", 5),
            minute=env_int("HOUSTON_UPLOAD_PURGE_BEAT_MINUTE_UTC", 0),
        ),
    },
    "recover-stuck-observation-processing": {
        "task": "houston.signals.tasks.recover_stuck_observation_processing_task",
        "schedule": crontab(
            minute=env_int("HOUSTON_OBSERVATION_STUCK_RECOVERY_BEAT_MINUTE_UTC", 15),
        ),
    },
}

# Auth rate-limit scopes (DRF ScopedRateThrottle); see DEFAULT_THROTTLE_RATES below.
AUTH_THROTTLE_SCOPE_LOGIN = "auth_login"
AUTH_THROTTLE_SCOPE_REFRESH = "auth_refresh"
AUTH_THROTTLE_SCOPE_REGISTER = "auth_register"
AUTH_THROTTLE_SCOPE_REGISTER_VALIDATE = "auth_register_validate"
AUTH_THROTTLE_SCOPE_INVITATION_ACCEPT = "auth_invitation_accept"
CHAT_THROTTLE_SCOPE_WS_TICKET = "chat_ws_ticket"

# Emergency / dev kill switch for auth throttling (prefer high DEBUG quotas over disabling).
HOUSTON_AUTH_THROTTLE_ENABLED = env_bool("HOUSTON_AUTH_THROTTLE_ENABLED", default=True)

_AUTH_THROTTLE_DEBUG_RATE = "1000/minute"


def _redis_throttle_cache_url() -> str:
    """Dedicated Redis DB for throttle counters (default db 3)."""
    explicit = os.getenv("HOUSTON_CACHE_REDIS_URL")
    if explicit:
        return explicit
    if "/" in REDIS_URL.rsplit("/", 1)[-1] and REDIS_URL.rsplit("/", 1)[-1].isdigit():
        return REDIS_URL.rsplit("/", 1)[0] + "/3"
    return f"{REDIS_URL.rstrip('/')}/3"


def _build_default_caches() -> dict:
    cache_redis_url = os.getenv("HOUSTON_CACHE_REDIS_URL")
    if cache_redis_url:
        return {
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": cache_redis_url,
            }
        }
    if DEBUG:
        return {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        }
    return {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _redis_throttle_cache_url(),
        }
    }


def _auth_throttle_rates() -> dict[str, str]:
    if DEBUG:
        rates = {
            AUTH_THROTTLE_SCOPE_LOGIN: _AUTH_THROTTLE_DEBUG_RATE,
            AUTH_THROTTLE_SCOPE_REFRESH: _AUTH_THROTTLE_DEBUG_RATE,
            AUTH_THROTTLE_SCOPE_REGISTER: _AUTH_THROTTLE_DEBUG_RATE,
            AUTH_THROTTLE_SCOPE_REGISTER_VALIDATE: _AUTH_THROTTLE_DEBUG_RATE,
            AUTH_THROTTLE_SCOPE_INVITATION_ACCEPT: _AUTH_THROTTLE_DEBUG_RATE,
            CHAT_THROTTLE_SCOPE_WS_TICKET: _AUTH_THROTTLE_DEBUG_RATE,
        }
    else:
        rates = {
            AUTH_THROTTLE_SCOPE_LOGIN: "10/minute",
            AUTH_THROTTLE_SCOPE_REFRESH: "30/minute",
            AUTH_THROTTLE_SCOPE_REGISTER: "5/hour",
            AUTH_THROTTLE_SCOPE_REGISTER_VALIDATE: "30/hour",
            AUTH_THROTTLE_SCOPE_INVITATION_ACCEPT: "10/hour",
            CHAT_THROTTLE_SCOPE_WS_TICKET: "30/minute",
        }

    env_overrides = {
        AUTH_THROTTLE_SCOPE_LOGIN: "HOUSTON_THROTTLE_AUTH_LOGIN",
        AUTH_THROTTLE_SCOPE_REFRESH: "HOUSTON_THROTTLE_AUTH_REFRESH",
        AUTH_THROTTLE_SCOPE_REGISTER: "HOUSTON_THROTTLE_AUTH_REGISTER",
        AUTH_THROTTLE_SCOPE_REGISTER_VALIDATE: "HOUSTON_THROTTLE_AUTH_REGISTER_VALIDATE",
        AUTH_THROTTLE_SCOPE_INVITATION_ACCEPT: "HOUSTON_THROTTLE_AUTH_INVITATION_ACCEPT",
        CHAT_THROTTLE_SCOPE_WS_TICKET: "HOUSTON_THROTTLE_CHAT_WS_TICKET",
    }
    for scope, env_name in env_overrides.items():
        override = os.getenv(env_name)
        if override:
            rates[scope] = override
    return rates


CACHES = _build_default_caches()

# InMemory is single-process only; Docker api (Daphne) + celery need a shared layer.
if env_bool("HOUSTON_CHANNELS_USE_IN_MEMORY", default=False):
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "houston.accounts.authentication.BearerAccessTokenAuthentication",
    ],
    "EXCEPTION_HANDLER": "houston.core.api.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": _auth_throttle_rates(),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Houston API",
    "DESCRIPTION": "Houston backend API contract",
    "VERSION": "0.1.0",
}

AUTHENTICATION_BACKENDS = [
    "houston.accounts.backends.IdentifierBackend",
]

HOUSTON_AUTH_ACCESS_TOKEN_TTL = timedelta(minutes=15)
HOUSTON_AUTH_REFRESH_TOKEN_TTL = timedelta(days=30)
HOUSTON_AUTH_ABSOLUTE_SESSION_TTL = timedelta(days=90)
HOUSTON_AUTH_TOKEN_SALT = env_str("HOUSTON_AUTH_TOKEN_SALT", "houston.auth.token")
HOUSTON_AUTH_TOKEN_PEPPER = env_str("HOUSTON_AUTH_TOKEN_PEPPER", SECRET_KEY)
HOUSTON_AUTH_TOKEN_BYTES = int(env_str("HOUSTON_AUTH_TOKEN_BYTES", "48"))
HOUSTON_DIRECTOR_INVITATION_TTL = timedelta(
    days=int(env_str("HOUSTON_DIRECTOR_INVITATION_TTL_DAYS", "7"))
)
HOUSTON_AUTH_TOKEN_GENERATION_MAX_ATTEMPTS = int(
    env_str("HOUSTON_AUTH_TOKEN_GENERATION_MAX_ATTEMPTS", "5")
)
HOUSTON_AUTH_REFRESH_COOKIE_NAME = env_str(
    "HOUSTON_AUTH_REFRESH_COOKIE_NAME",
    "houston_refresh_token",
)
HOUSTON_AUTH_REFRESH_COOKIE_HTTPONLY = True
HOUSTON_AUTH_REFRESH_COOKIE_SAMESITE = env_str(
    "HOUSTON_AUTH_REFRESH_COOKIE_SAMESITE",
    "Lax",
)
HOUSTON_AUTH_REFRESH_COOKIE_PATH = env_str(
    "HOUSTON_AUTH_REFRESH_COOKIE_PATH",
    "/api/v1/auth/",
)
HOUSTON_AUTH_REFRESH_COOKIE_SECURE = env_bool(
    "HOUSTON_AUTH_REFRESH_COOKIE_SECURE",
    default=not DEBUG,
)

HOUSTON_REGISTRATION_INVITE_CODES = env_list("HOUSTON_REGISTRATION_INVITE_CODES", "")

HOUSTON_CHAT_WS_TICKET_TTL_SECONDS = env_int("HOUSTON_CHAT_WS_TICKET_TTL_SECONDS", 60)
HOUSTON_CHAT_WS_AUTH_TIMEOUT_SECONDS = env_int("HOUSTON_CHAT_WS_AUTH_TIMEOUT_SECONDS", 5)
HOUSTON_CHAT_WS_TICKET_SALT = env_str(
    "HOUSTON_CHAT_WS_TICKET_SALT",
    "houston.chat.ws_ticket",
)
HOUSTON_REALTIME_WS_TICKET_TTL_SECONDS = env_int("HOUSTON_REALTIME_WS_TICKET_TTL_SECONDS", 60)
HOUSTON_REALTIME_WS_AUTH_TIMEOUT_SECONDS = env_int("HOUSTON_REALTIME_WS_AUTH_TIMEOUT_SECONDS", 5)
HOUSTON_REALTIME_WS_TICKET_SALT = env_str(
    "HOUSTON_REALTIME_WS_TICKET_SALT",
    "houston.realtime.ws_ticket",
)
HOUSTON_CHAT_MESSAGE_RETENTION_DAYS = env_int(
    "HOUSTON_CHAT_MESSAGE_RETENTION_DAYS",
    7,
)
HOUSTON_CHAT_PURGE_BATCH_SIZE = env_int("HOUSTON_CHAT_PURGE_BATCH_SIZE", 1000)
HOUSTON_CHAT_MESSAGE_SEND_RATE_LIMIT_PER_MINUTE = env_int(
    "HOUSTON_CHAT_MESSAGE_SEND_RATE_LIMIT_PER_MINUTE",
    30,
)
HOUSTON_CHAT_RATE_LIMIT_ENABLED = env_bool("HOUSTON_CHAT_RATE_LIMIT_ENABLED", default=True)

OPENAI_API_KEY = env_str("OPENAI_API_KEY", "")

HOUSTON_LOG_LEVEL = env_str("HOUSTON_LOG_LEVEL", "INFO")
HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS = env_int(
    "HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS",
    HOUSTON_AI_OBSERVATION_TIMEOUT_SECONDS * 2,
)
HOUSTON_CELERY_OBSERVATION_PIPELINE_SOFT_TIME_LIMIT_SECONDS = env_int(
    "HOUSTON_CELERY_OBSERVATION_PIPELINE_SOFT_TIME_LIMIT_SECONDS",
    HOUSTON_AI_OBSERVATION_TIMEOUT_SECONDS + 60,
)
HOUSTON_CELERY_OBSERVATION_PIPELINE_TIME_LIMIT_SECONDS = env_int(
    "HOUSTON_CELERY_OBSERVATION_PIPELINE_TIME_LIMIT_SECONDS",
    HOUSTON_AI_OBSERVATION_TIMEOUT_SECONDS + 120,
)
HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS = env_int(
    "HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS",
    3300,
)
HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS = env_int(
    "HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS",
    3600,
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "houston_structured": {
            "()": "houston.core.logging_support.HoustonStructuredFormatter",
            "format": "%(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "houston_structured",
        },
    },
    "loggers": {
        "houston": {
            "level": HOUSTON_LOG_LEVEL,
            "propagate": True,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": HOUSTON_LOG_LEVEL,
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]
