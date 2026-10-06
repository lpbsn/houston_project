import os

from celery import Celery

from config.celery_compat import apply_rabbitmq4_qos_compat

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Temporary kombu#2481 backport; remove with config/celery_compat.py.
apply_rabbitmq4_qos_compat()

app = Celery("houston")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
