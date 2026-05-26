import uuid

from django.utils import timezone

from houston.core.events import EventEnvelope


def test_event_envelope_generates_default_id_and_timestamp():
    event = EventEnvelope(
        event_type="SignalCreated",
        category="business",
        subject_type="Signal",
        subject_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
    )

    assert isinstance(event.id, uuid.UUID)
    assert timezone.is_aware(event.occurred_at) is True
    assert event.event_version == 1


def test_event_envelope_optional_fields_default_to_none():
    event = EventEnvelope(
        event_type="SignalCreated",
        category="business",
        subject_type="Signal",
        subject_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
    )

    assert event.organization_id is None
    assert event.establishment_id is None
    assert event.actor_id is None
    assert event.causation_id is None
    assert event.idempotency_key is None


def test_event_envelope_payload_defaults_to_empty_mapping():
    first_event = EventEnvelope(
        event_type="SignalCreated",
        category="business",
        subject_type="Signal",
        subject_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
    )
    second_event = EventEnvelope(
        event_type="ActionValidated",
        category="audit",
        subject_type="Action",
        subject_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
    )

    assert first_event.payload == {}
    assert second_event.payload == {}
    assert first_event.payload is not second_event.payload
