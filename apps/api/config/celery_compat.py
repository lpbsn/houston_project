from __future__ import annotations

from importlib.metadata import version as package_version

from kombu.transport import pyamqp
from kombu.transport.pyamqp import version_string_as_tuple

_KOMBU_NATIVE_RABBITMQ4_QOS_VERSION = (5, 7)
_HOUSTON_COMPAT_MARKER = "__houston_rabbitmq4_qos_compat__"


def _kombu_major_minor() -> tuple[int, int]:
    major, minor, *_ = package_version("kombu").split(".")
    return int(major), int(minor)


def _qos_semantics_matches_spec(self, connection):
    props = connection.server_properties
    if props.get("product") == "RabbitMQ":
        version_str = props.get("version")
        if not version_str:
            return True
        version = version_string_as_tuple(version_str)
        return version < (3, 3) or version >= (4, 0)
    return True


def apply_rabbitmq4_qos_compat() -> bool:
    """Backport Kombu's RabbitMQ 4 QoS semantics until Kombu 5.7+ is installed.

    Kombu 5.6.x treats RabbitMQ >=3.3 as using global QoS semantics. RabbitMQ 4
    removed global QoS for classic queues, so Celery must use per-consumer QoS.
    This mirrors celery/kombu#2481 and becomes a no-op once Kombu 5.7+ is used.
    """

    if _kombu_major_minor() >= _KOMBU_NATIVE_RABBITMQ4_QOS_VERSION:
        return False

    current = pyamqp.Transport.qos_semantics_matches_spec
    if getattr(current, _HOUSTON_COMPAT_MARKER, False):
        return False

    setattr(_qos_semantics_matches_spec, _HOUSTON_COMPAT_MARKER, True)
    pyamqp.Transport.qos_semantics_matches_spec = _qos_semantics_matches_spec
    return True
