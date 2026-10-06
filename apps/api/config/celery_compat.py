from __future__ import annotations

from importlib.metadata import version as package_version

from kombu.transport import pyamqp
from kombu.utils.text import version_string_as_tuple

# Delete this module, its call in config/celery.py, and
# houston/core/tests/test_celery_compat.py when Kombu 5.7+ is locked.
_KOMBU_NATIVE_RABBITMQ4_QOS_VERSION = (5, 7)
_HOUSTON_COMPAT_MARKER = "__houston_rabbitmq4_qos_compat__"


def _kombu_major_minor() -> tuple[int, int]:
    major, minor, *_ = package_version("kombu").split(".")
    return int(major), int(minor)


def _qos_semantics_matches_spec(self, connection):
    # celery/kombu#2481: RabbitMQ 4 classic queues no longer accept global QoS.
    props = connection.server_properties
    if props.get("product") == "RabbitMQ":
        version_str = props.get("version")
        if not version_str:
            return True
        version = version_string_as_tuple(version_str)
        return version < (3, 3) or version >= (4, 0)
    return True


def apply_rabbitmq4_qos_compat() -> bool:
    """Patch pyamqp.Transport until the installed Kombu includes kombu#2481.

    Celery decides `basic.qos(global=...)` with
    `not connection.qos_semantics_matches_spec`, and kombu Connection
    delegates that to `Transport.qos_semantics_matches_spec`. Kombu 5.6.x
    returns False for every RabbitMQ >= 3.3, so workers send global QoS and
    RabbitMQ 4 rejects it. This replaces only that method.
    """

    if _kombu_major_minor() >= _KOMBU_NATIVE_RABBITMQ4_QOS_VERSION:
        return False

    current = pyamqp.Transport.qos_semantics_matches_spec
    if getattr(current, _HOUSTON_COMPAT_MARKER, False):
        return False

    setattr(_qos_semantics_matches_spec, _HOUSTON_COMPAT_MARKER, True)
    pyamqp.Transport.qos_semantics_matches_spec = _qos_semantics_matches_spec
    return True
