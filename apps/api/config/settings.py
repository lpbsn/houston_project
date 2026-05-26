import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(int(default))).lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str) -> list[str]:
    value = env_str(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = env_str("DJANGO_SECRET_KEY", "replace-me-for-local-dev")
DEBUG = env_bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_str("POSTGRES_DB", "houston"),
        "USER": env_str("POSTGRES_USER", "houston"),
        "PASSWORD": env_str("POSTGRES_PASSWORD", "houston"),
        "HOST": env_str("POSTGRES_HOST", "postgres"),
        "PORT": env_str("POSTGRES_PORT", "5432"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env_str("REDIS_URL", "redis://redis:6379/0")
CELERY_BROKER_URL = env_str("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = env_str("CELERY_RESULT_BACKEND", "redis://redis:6379/2")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
        if DEBUG
        else "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Houston API",
    "DESCRIPTION": "Phase 0.1 foundations schema",
    "VERSION": "0.1.0",
}
