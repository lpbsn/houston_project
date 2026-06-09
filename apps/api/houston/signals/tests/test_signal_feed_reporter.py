from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from houston.accounts.models import User
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.signals.models import Signal, SignalSourceObservation
from houston.signals.reporter_display import format_reporter_display_name
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    create_observation,
    login,
    signal_feed_url,
)

_LEAK_MARKER = "LEAK_RAW_OBSERVATION_TEXT_DO_NOT_EXPOSE"


def _create_signal(membership, *, title: str = "Reporter signal"):
    return create_minimal_v3_signal(membership, title=title)


def _feed_item_for_signal(api_client, membership, signal: Signal):
    token = login(api_client, user=membership.user)
    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )
    assert response.status_code == 200
    for item in response.json()["items"]:
        if item["id"] == str(signal.id):
            return item
    pytest.fail("signal not found in feed")


def test_format_reporter_display_name_abbreviates_first_last():
    user = User(first_name="Marie", last_name="Renaud")
    assert format_reporter_display_name(user) == "Marie R."


def test_format_reporter_display_name_from_full_name_two_tokens():
    user = User(first_name="", last_name="")
    user.get_full_name = lambda: "Alice Lambert"  # type: ignore[method-assign]
    assert format_reporter_display_name(user) == "Alice L."


def test_format_reporter_display_name_single_token():
    user = User(first_name="Cher", last_name="")
    assert format_reporter_display_name(user) == "Cher"


def test_format_reporter_display_name_empty_returns_none():
    user = User(first_name="", last_name="", email="only@example.com", username="onlyuser")
    assert format_reporter_display_name(user) is None


@pytest.mark.django_db
def test_feed_reporter_display_name_abbreviated(api_client):
    membership = build_api_membership()
    membership.user.first_name = "Marie"
    membership.user.last_name = "Renaud"
    membership.user.save(update_fields=["first_name", "last_name"])

    signal = _create_signal(membership)
    observation = create_observation(membership=membership, text="A" * 20)
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )

    item = _feed_item_for_signal(api_client, membership, signal)
    assert item["reporter_display_name"] == "Marie R."


@pytest.mark.django_db
def test_feed_reporter_uses_oldest_observation_not_link_created_at(api_client):
    marie_membership = build_api_membership()
    establishment = marie_membership.establishment
    marie_membership.user.first_name = "Marie"
    marie_membership.user.last_name = "Renaud"
    marie_membership.user.save(update_fields=["first_name", "last_name"])
    alice_user = User.objects.create_user(
        username=f"alice_{uuid.uuid4().hex[:6]}",
        email=f"alice_{uuid.uuid4().hex[:6]}@example.com",
        password=TEST_PASSWORD,
        first_name="Alice",
        last_name="Lambert",
        status=User.Status.ACTIVE,
    )
    alice_membership = EstablishmentMembership.objects.create(
        user=alice_user,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    signal = _create_signal(marie_membership)
    now = timezone.now()
    older_obs = create_observation(membership=marie_membership, text="A" * 20)
    newer_obs = create_observation(membership=alice_membership, text="B" * 20)
    Observation = older_obs.__class__
    Observation.objects.filter(id=newer_obs.id).update(created_at=now)
    Observation.objects.filter(id=older_obs.id).update(created_at=now - timedelta(hours=1))

    SignalSourceObservation.objects.create(
        signal=signal,
        observation=newer_obs,
        link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
    )
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=older_obs,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )

    item = _feed_item_for_signal(api_client, marie_membership, signal)
    assert item["reporter_display_name"] == "Marie R."


@pytest.mark.django_db
def test_feed_reporter_tiebreaker_observation_id(api_client):
    membership = build_api_membership()
    membership.user.first_name = "Marie"
    membership.user.last_name = "Renaud"
    membership.user.save(update_fields=["first_name", "last_name"])

    alice_user = User.objects.create_user(
        username=f"alice_{uuid.uuid4().hex[:6]}",
        email=f"alice_{uuid.uuid4().hex[:6]}@example.com",
        password=TEST_PASSWORD,
        first_name="Alice",
        last_name="Lambert",
        status=User.Status.ACTIVE,
    )
    alice_membership = EstablishmentMembership.objects.create(
        user=alice_user,
        establishment=membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    signal = _create_signal(membership)
    now = timezone.now()
    obs_a = create_observation(membership=membership, text="A" * 20)
    obs_b = create_observation(membership=alice_membership, text="B" * 20)
    Observation = obs_a.__class__
    Observation.objects.filter(id__in=[obs_a.id, obs_b.id]).update(created_at=now)

    first_obs, second_obs = (obs_a, obs_b) if obs_a.id < obs_b.id else (obs_b, obs_a)
    first_membership = membership if first_obs.id == obs_a.id else alice_membership
    expected_name = "Marie R." if first_membership.user.last_name == "Renaud" else "Alice L."

    SignalSourceObservation.objects.create(
        signal=signal,
        observation=obs_a,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=obs_b,
        link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
    )

    item = _feed_item_for_signal(api_client, membership, signal)
    assert item["reporter_display_name"] == expected_name


@pytest.mark.django_db
def test_feed_reporter_null_without_link(api_client):
    membership = build_api_membership()
    signal = _create_signal(membership)

    item = _feed_item_for_signal(api_client, membership, signal)
    assert item["reporter_display_name"] is None


@pytest.mark.django_db
def test_feed_reporter_null_when_only_email_username(api_client):
    membership = build_api_membership()
    user = membership.user
    user.first_name = ""
    user.last_name = ""
    user.save(update_fields=["first_name", "last_name"])

    signal = _create_signal(membership)
    observation = create_observation(membership=membership, text="A" * 20)
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )

    token = login(api_client, user=membership.user)
    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )
    assert response.status_code == 200
    item = next(i for i in response.json()["items"] if i["id"] == str(signal.id))
    assert item["reporter_display_name"] is None
    body = response.content.decode()
    if user.email:
        assert user.email not in body
    assert user.username not in body


@pytest.mark.django_db
def test_feed_reporter_never_leaks_raw_observation_text(api_client):
    membership = build_api_membership()
    signal = _create_signal(membership)
    observation = create_observation(membership=membership, text=_LEAK_MARKER)
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )

    token = login(api_client, user=membership.user)
    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.content.decode()
    assert _LEAK_MARKER not in body
    assert "raw_text" not in body
