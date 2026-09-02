from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from houston.accounts.models import User
from houston.establishments.konoha_dataset_actors import (
    ESTABLISHMENT_AKATSUKI,
    ESTABLISHMENT_ANBU,
    EXPECTED_MANAGERS_PER_POLE,
    EXPECTED_STAFF_PER_POLE,
    KONOHA_DATASET_SEATS,
    LOCAL_DATASET_PASSWORD,
    NARUTO_EMAIL,
    NARUTO_USERNAME,
    ORGANIZATION_NAME,
    POLE_HOTEL,
    KonohaDatasetActorsError,
    SeatAction,
    classify_seat,
    preflight_konoha_dataset_actors,
    provision_konoha_dataset_actors,
)
from houston.establishments.membership_scope import MembershipScopeInput, MembershipScopeType
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipScope,
)
from houston.establishments.services import invite_membership_for_establishment
from houston.organizations.models import Organization
from houston.testing.factories import TEST_PASSWORD
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db

LOCAL_DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "houston",
        "USER": "houston",
        "PASSWORD": "houston",
        "HOST": "postgres",
        "PORT": "5432",
    }
}

ANBU_POLES = (
    ("hotel", "Hôtel"),
    ("restaurant_ishiraku", "Ishiraku Ramen"),
    ("restaurant_yakinuku", "Yakinuku Grill"),
    ("coworking", "Coworking"),
    ("maintenance", "Maintenance"),
    ("communication", "Communication"),
)
AKATSUKI_POLES = (
    ("commerce", "Commerce"),
    ("salle_de_sport", "Basic Fit"),
    ("loisirs", "EMEA"),
    ("evenements_privatisations", "Événements & privatisations"),
    ("maintenance", "Maintenance"),
    ("communication", "Communication"),
)


def _create_named_user(
    *,
    username: str,
    email: str,
    first_name: str,
    last_name: str,
    status: str = User.Status.ACTIVE,
) -> User:
    user = User.objects.create_user(
        username=username,
        email=email,
        password=TEST_PASSWORD,
        first_name=first_name,
        last_name=last_name,
        status=status,
    )
    if status == User.Status.ACTIVE:
        from houston.accounts.legal_services import grant_current_legal_defaults

        grant_current_legal_defaults(user=user)
    return user


def _create_scoped_member(
    *,
    username: str,
    email: str,
    first_name: str,
    last_name: str,
    establishment: Establishment,
    role: str,
    business_unit,
) -> EstablishmentMembership:
    user = _create_named_user(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    return membership


def _build_konoha_runtime(*, include_held_seats: bool = True):
    organization = Organization.objects.create(name=ORGANIZATION_NAME)
    anbu = Establishment.objects.create(
        name=ESTABLISHMENT_ANBU,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    akatsuki = Establishment.objects.create(
        name=ESTABLISHMENT_AKATSUKI,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    anbu_poles = {
        label: create_business_unit(establishment=anbu, key=key, label=label)
        for key, label in ANBU_POLES
    }
    akatsuki_poles = {
        label: create_business_unit(establishment=akatsuki, key=key, label=label)
        for key, label in AKATSUKI_POLES
    }
    naruto = _create_named_user(
        username=NARUTO_USERNAME,
        email=NARUTO_EMAIL,
        first_name="Naruto",
        last_name="Uzumaki",
    )
    naruto_anbu = EstablishmentMembership.objects.create(
        user=naruto,
        establishment=anbu,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    naruto_akatsuki = EstablishmentMembership.objects.create(
        user=naruto,
        establishment=akatsuki,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    if include_held_seats:
        _create_scoped_member(
            username="ishiraku",
            email="ishiraku@konoha.com",
            first_name="Tehuci",
            last_name="Ishiraku",
            establishment=anbu,
            role=EstablishmentMembership.Role.MANAGER,
            business_unit=anbu_poles["Ishiraku Ramen"],
        )
        _create_scoped_member(
            username="choji",
            email="choji@konoha.com",
            first_name="Choji",
            last_name="Akimichi",
            establishment=anbu,
            role=EstablishmentMembership.Role.STAFF,
            business_unit=anbu_poles["Ishiraku Ramen"],
        )
        _create_scoped_member(
            username="zabuza",
            email="zabuza@konoha.com",
            first_name="Zabuza",
            last_name="Momochi",
            establishment=anbu,
            role=EstablishmentMembership.Role.MANAGER,
            business_unit=anbu_poles["Yakinuku Grill"],
        )
        _create_scoped_member(
            username="haku",
            email="haku@konoha.com",
            first_name="Haku",
            last_name="Momochi",
            establishment=anbu,
            role=EstablishmentMembership.Role.STAFF,
            business_unit=anbu_poles["Yakinuku Grill"],
        )
        _create_scoped_member(
            username="tobirama",
            email="tobirama@konoha.com",
            first_name="Tobirama",
            last_name="Senju",
            establishment=anbu,
            role=EstablishmentMembership.Role.MANAGER,
            business_unit=anbu_poles["Communication"],
        )
    return {
        "anbu": anbu,
        "akatsuki": akatsuki,
        "anbu_poles": anbu_poles,
        "akatsuki_poles": akatsuki_poles,
        "naruto": naruto,
        "naruto_anbu": naruto_anbu,
        "naruto_akatsuki": naruto_akatsuki,
    }


def _naruto_fingerprint(runtime) -> tuple:
    naruto = User.objects.get(pk=runtime["naruto"].pk)
    anbu = EstablishmentMembership.objects.get(pk=runtime["naruto_anbu"].pk)
    akatsuki = EstablishmentMembership.objects.get(pk=runtime["naruto_akatsuki"].pk)
    return (
        naruto.id,
        naruto.username,
        naruto.email,
        naruto.status,
        naruto.first_name,
        naruto.last_name,
        anbu.role,
        anbu.status,
        akatsuki.role,
        akatsuki.status,
        MembershipScope.objects.filter(membership_id=anbu.id).count(),
        MembershipScope.objects.filter(membership_id=akatsuki.id).count(),
    )


def test_roster_has_fifty_five_named_seats():
    emails = [seat.email for seat in KONOHA_DATASET_SEATS]
    assert len(KONOHA_DATASET_SEATS) == 55
    assert len(set(emails)) == 55
    assert all(seat.first_name.strip() and seat.last_name.strip() for seat in KONOHA_DATASET_SEATS)
    assert {seat.role for seat in KONOHA_DATASET_SEATS} <= {
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    }
    assert {seat.establishment_name for seat in KONOHA_DATASET_SEATS} == {
        ESTABLISHMENT_ANBU,
        ESTABLISHMENT_AKATSUKI,
    }
    held_emails = {
        "ishiraku@konoha.com",
        "choji@konoha.com",
        "zabuza@konoha.com",
        "haku@konoha.com",
        "tobirama@konoha.com",
        NARUTO_EMAIL,
    }
    assert held_emails.isdisjoint(emails)


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_preflight_mismatch_blocks_all_writes():
    runtime = _build_konoha_runtime()
    _create_scoped_member(
        username="extra_hotel",
        email="extra.hotel@konoha.com",
        first_name="Extra",
        last_name="Hotel",
        establishment=runtime["anbu"],
        role=EstablishmentMembership.Role.STAFF,
        business_unit=runtime["anbu_poles"][POLE_HOTEL],
    )
    before = User.objects.filter(email__iendswith="@konoha.test").count()
    before_naruto = _naruto_fingerprint(runtime)

    with pytest.raises(KonohaDatasetActorsError, match="ANBU/Hôtel"):
        provision_konoha_dataset_actors(dry_run=False)

    assert User.objects.filter(email__iendswith="@konoha.test").count() == before
    assert _naruto_fingerprint(runtime) == before_naruto


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_missing_naruto_blocks_writes():
    _build_konoha_runtime()
    User.objects.filter(username=NARUTO_USERNAME).update(username="not-naruto")

    with pytest.raises(KonohaDatasetActorsError, match="Naruto not found"):
        provision_konoha_dataset_actors(dry_run=False)

    assert not User.objects.filter(email__iendswith="@konoha.test").exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_missing_held_seat_fails_exact_projection():
    _build_konoha_runtime(include_held_seats=False)

    with pytest.raises(KonohaDatasetActorsError, match="Ishiraku Ramen"):
        provision_konoha_dataset_actors(dry_run=True)

    assert not User.objects.filter(email__iendswith="@konoha.test").exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_provision_invite_accept_then_skip_is_idempotent(monkeypatch):
    runtime = _build_konoha_runtime()
    before_naruto = _naruto_fingerprint(runtime)
    invite_calls: list[str] = []
    real_invite = invite_membership_for_establishment

    def tracking_invite(**kwargs):
        invite_calls.append(kwargs["email"])
        return real_invite(**kwargs)

    monkeypatch.setattr(
        "houston.establishments.konoha_dataset_actors.invite_membership_for_establishment",
        tracking_invite,
    )

    first = provision_konoha_dataset_actors(dry_run=False)
    assert first.invited_accepted == 55
    assert first.skipped == 0
    assert first.reinvited_accepted == 0
    created = User.objects.filter(
        email__iendswith="@konoha.test",
        status=User.Status.ACTIVE,
    )
    assert created.count() == 55
    assert _naruto_fingerprint(runtime) == before_naruto

    for establishment in (runtime["anbu"], runtime["akatsuki"]):
        poles = (
            runtime["anbu_poles"]
            if establishment.name == ESTABLISHMENT_ANBU
            else runtime["akatsuki_poles"]
        )
        for pole in poles.values():
            managers = 0
            staff = 0
            for membership in EstablishmentMembership.objects.filter(
                establishment=establishment,
                status=EstablishmentMembership.Status.ACTIVE,
                role__in={
                    EstablishmentMembership.Role.MANAGER,
                    EstablishmentMembership.Role.STAFF,
                },
            ):
                scope_ids = set(
                    MembershipScope.objects.filter(membership=membership).values_list(
                        "business_unit_id",
                        flat=True,
                    )
                )
                if scope_ids == {pole.id}:
                    if membership.role == EstablishmentMembership.Role.MANAGER:
                        managers += 1
                    else:
                        staff += 1
            assert managers == EXPECTED_MANAGERS_PER_POLE
            assert staff == EXPECTED_STAFF_PER_POLE

    invite_calls.clear()
    second = provision_konoha_dataset_actors(dry_run=False)
    assert second.skipped == 55
    assert second.invited_accepted == 0
    assert invite_calls == []
    assert _naruto_fingerprint(runtime) == before_naruto


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_pending_invited_seat_is_reinvited_not_invited(monkeypatch):
    runtime = _build_konoha_runtime()
    hotel = runtime["anbu_poles"][POLE_HOTEL]
    seat = next(
        item for item in KONOHA_DATASET_SEATS if item.email == "anbu.hotel.mgr1@konoha.test"
    )
    invite_membership_for_establishment(
        current_membership=runtime["naruto_anbu"],
        establishment_id=runtime["anbu"].id,
        email=seat.email,
        first_name=seat.first_name,
        last_name=seat.last_name,
        role=seat.role,
        scopes=[
            MembershipScopeInput(
                scope_type=MembershipScopeType.BUSINESS_UNIT,
                scope_id=hotel.id,
            )
        ],
    )
    pending = User.objects.get(email=seat.email)
    membership = EstablishmentMembership.objects.get(user=pending, establishment=runtime["anbu"])
    assert pending.status == User.Status.PENDING
    assert membership.status == EstablishmentMembership.Status.INVITED

    classification = classify_seat(
        seat,
        establishment=runtime["anbu"],
        business_unit=hotel,
    )
    assert classification.action == SeatAction.REINVITE_ACCEPT

    invite_calls: list[str] = []
    real_invite = invite_membership_for_establishment

    def tracking_invite(**kwargs):
        invite_calls.append(kwargs["email"])
        return real_invite(**kwargs)

    monkeypatch.setattr(
        "houston.establishments.konoha_dataset_actors.invite_membership_for_establishment",
        tracking_invite,
    )
    result = provision_konoha_dataset_actors(dry_run=False)
    assert result.reinvited_accepted == 1
    assert result.invited_accepted == 54
    assert seat.email not in invite_calls
    pending.refresh_from_db()
    membership.refresh_from_db()
    assert pending.status == User.Status.ACTIVE
    assert membership.status == EstablishmentMembership.Status.ACTIVE
    assert User.objects.filter(email=seat.email).count() == 1
    assert pending.check_password(LOCAL_DATASET_PASSWORD)


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_classify_mismatch_wrong_role():
    runtime = _build_konoha_runtime()
    hotel = runtime["anbu_poles"][POLE_HOTEL]
    seat = next(
        item for item in KONOHA_DATASET_SEATS if item.email == "anbu.hotel.mgr1@konoha.test"
    )
    _create_scoped_member(
        username="anbu.hotel.mgr1",
        email=seat.email,
        first_name=seat.first_name,
        last_name=seat.last_name,
        establishment=runtime["anbu"],
        role=EstablishmentMembership.Role.STAFF,
        business_unit=hotel,
    )
    classification = classify_seat(
        seat,
        establishment=runtime["anbu"],
        business_unit=hotel,
    )
    assert classification.action == SeatAction.ERROR
    preflight = preflight_konoha_dataset_actors()
    assert preflight.errors
    with pytest.raises(KonohaDatasetActorsError):
        provision_konoha_dataset_actors(dry_run=False)
    assert User.objects.filter(email__iendswith="@konoha.test").count() == 1


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_dry_run_does_not_create_users():
    _build_konoha_runtime()
    result = provision_konoha_dataset_actors(dry_run=True)
    assert result.dry_run is True
    assert result.invited_accepted == 55
    assert not User.objects.filter(email__iendswith="@konoha.test").exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_command_requires_dry_run_or_confirm():
    stdout = StringIO()
    with pytest.raises(CommandError, match="--confirm"):
        call_command("provision_konoha_dataset_actors", stdout=stdout)
    assert not User.objects.filter(email__iendswith="@konoha.test").exists()


@override_settings(DEBUG=False, DATABASES=LOCAL_DATABASES)
def test_command_refuses_without_debug():
    _build_konoha_runtime()
    with pytest.raises(CommandError, match="DJANGO_DEBUG"):
        call_command("provision_konoha_dataset_actors", "--dry-run")
