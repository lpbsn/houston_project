from __future__ import annotations

from types import SimpleNamespace

from celery.worker.consumer.tasks import Tasks
from config.celery import app
from config.celery_compat import (
    _HOUSTON_COMPAT_MARKER,
    _KOMBU_NATIVE_RABBITMQ4_QOS_VERSION,
    _kombu_major_minor,
    apply_rabbitmq4_qos_compat,
)
from django.conf import settings
from kombu import Connection
from kombu.transport import pyamqp


def _broker_connection(**server_properties):
    return SimpleNamespace(server_properties=server_properties)


def _spore_pyamqp_transport():
    return Connection(settings.CELERY_BROKER_URL).transport


def _celery_qos_global(**server_properties):
    transport = _spore_pyamqp_transport()
    consumer = SimpleNamespace(
        connection=SimpleNamespace(
            qos_semantics_matches_spec=transport.qos_semantics_matches_spec(
                _broker_connection(**server_properties)
            ),
            transport=transport,
        ),
        app=app,
    )
    return Tasks.__new__(Tasks).qos_global(consumer)


def test_delete_compat_when_kombu_ships_native_rabbitmq4_qos():
    assert _kombu_major_minor() < _KOMBU_NATIVE_RABBITMQ4_QOS_VERSION
    assert getattr(
        pyamqp.Transport.qos_semantics_matches_spec,
        _HOUSTON_COMPAT_MARKER,
        False,
    )


def test_apply_is_idempotent_and_skips_kombu_with_native_fix(monkeypatch):
    assert apply_rabbitmq4_qos_compat() is False

    monkeypatch.setattr(
        "config.celery_compat._kombu_major_minor",
        lambda: _KOMBU_NATIVE_RABBITMQ4_QOS_VERSION,
    )
    assert apply_rabbitmq4_qos_compat() is False
    assert getattr(
        pyamqp.Transport.qos_semantics_matches_spec,
        _HOUSTON_COMPAT_MARKER,
        False,
    )


def test_kombu_pyamqp_transport_matches_upstream_2481_boundaries():
    transport = _spore_pyamqp_transport()
    assert isinstance(transport, pyamqp.Transport)

    assert (
        transport.qos_semantics_matches_spec(
            _broker_connection(product="ActiveMQ", version="5.0.0")
        )
        is True
    )
    assert (
        transport.qos_semantics_matches_spec(
            _broker_connection(product="RabbitMQ", version="3.2.4")
        )
        is True
    )
    assert (
        transport.qos_semantics_matches_spec(
            _broker_connection(product="RabbitMQ", version="3.3.0")
        )
        is False
    )
    assert (
        transport.qos_semantics_matches_spec(
            _broker_connection(product="RabbitMQ", version="3.13.7")
        )
        is False
    )
    assert (
        transport.qos_semantics_matches_spec(
            _broker_connection(product="RabbitMQ", version="4.0.0")
        )
        is True
    )
    assert (
        transport.qos_semantics_matches_spec(
            _broker_connection(product="RabbitMQ", version="4.3.0")
        )
        is True
    )
    assert (
        transport.qos_semantics_matches_spec(_broker_connection(product="RabbitMQ"))
        is True
    )


def test_celery_worker_uses_per_consumer_qos_on_rabbitmq4():
    assert _celery_qos_global(product="RabbitMQ", version="4.3.0") is False
    assert _celery_qos_global(product="RabbitMQ", version="4.0.0") is False
    assert _celery_qos_global(product="RabbitMQ") is False


def test_celery_worker_keeps_global_qos_on_rabbitmq_3_3_to_3_x():
    assert _celery_qos_global(product="RabbitMQ", version="3.3.0") is True
    assert _celery_qos_global(product="RabbitMQ", version="3.13.7") is True
    assert _celery_qos_global(product="RabbitMQ", version="3.2.4") is False
