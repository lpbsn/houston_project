from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from django.db import connections
from django.utils import timezone

from houston.brain.admission import admit_brain_work
from houston.brain.errors import BrainAccessDenied, BrainCapacityUnavailable, BrainWorkError
from houston.brain.models import BrainAnalysis, BrainExtraction, BrainReporting, BrainSlot
from houston.brain.records import EXTRACTOR_ID, EXTRACTOR_VERSION
from houston.establishments.models import EstablishmentMembership
from houston.testing.factories import create_establishment, create_membership

pytestmark = pytest.mark.django_db


def _reporting(establishment, author, *, ready=True):
    reporting = BrainReporting.objects.create(
        establishment=establishment,
        author=author,
        original_filename="mars.csv",
        content_type="text/csv",
        source_format=BrainReporting.SourceFormat.CSV,
        content_sha256="a" * 64,
        storage_key=f"brain/reportings/{establishment.id}/original",
        byte_size=8,
        status=BrainReporting.Status.READY if ready else BrainReporting.Status.DRAFT,
        period_start=None,
        period_end=None,
        period_confirmed_at=None,
    )
    if ready:
        reporting.period_start = date(2026, 3, 1)
        reporting.period_end = date(2026, 4, 1)
        reporting.period_confirmed_at = timezone.now()
        reporting.save()
        BrainExtraction.objects.create(
            reporting=reporting,
            extractor_id=EXTRACTOR_ID,
            extractor_version=EXTRACTOR_VERSION,
            source_sha256=reporting.content_sha256,
            payload={"measures": [], "qualitative": []},
        )
    return reporting


def _admit(user, establishment, reporting, key="demande-1"):
    return admit_brain_work(
        user=user,
        establishment_id=establishment.id,
        reporting_id=reporting.id,
        idempotency_key=key,
    )


def test_owner_admission_inserts_one_queued_analysis_and_slot():
    establishment = create_establishment(name="Brain hotel", timezone="Europe/Paris")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    reporting = _reporting(establishment, owner.user)
    analysis = _admit(owner.user, establishment, reporting)
    assert analysis.status == BrainAnalysis.Status.QUEUED
    assert analysis.author_id == owner.user_id
    assert analysis.configuration["extractor_id"] == EXTRACTOR_ID
    assert analysis.configuration["knowledge"]["selection"] == "none"
    assert analysis.configuration["knowledge"]["version_id"] is None
    assert analysis.configuration["knowledge"]["formulation"] == ""
    slot = BrainSlot.objects.get(analysis=analysis)
    assert slot.kind == BrainSlot.Kind.ANALYSIS
    assert slot.status == BrainSlot.Status.QUEUED
    assert slot.token == analysis.attempt_token
    assert slot.establishment_id == establishment.id


def test_same_key_at_full_capacity_returns_the_analysis_and_a_new_key_is_refused(settings):
    settings.HOUSTON_BRAIN_MAX_QUEUED_AND_RUNNING = 1
    establishment = create_establishment(name="Brain capacity")
    other = create_establishment(name="Brain capacity other")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    other_owner = create_membership(
        establishment=other,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    reporting = _reporting(establishment, owner.user)
    other_reporting = _reporting(other, other_owner.user)
    first = _admit(owner.user, establishment, reporting, key="meme-demande")
    again = _admit(owner.user, establishment, reporting, key="meme-demande")
    assert again.id == first.id
    assert BrainAnalysis.objects.count() == 1
    assert BrainSlot.objects.count() == 1
    active = _admit(owner.user, establishment, reporting, key="autre-demande")
    assert active.id == first.id
    with pytest.raises(BrainCapacityUnavailable):
        _admit(other_owner.user, other, other_reporting, key="nouvelle-demande")
    assert BrainAnalysis.objects.count() == 1


def test_staff_and_another_establishment_director_are_denied_without_the_work():
    establishment = create_establishment(name="Brain access")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    other = create_establishment(name="Autre hotel")
    outsider = create_membership(
        establishment=other,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    reporting = _reporting(establishment, owner.user)
    analysis = _admit(owner.user, establishment, reporting, key="privee")
    for user in (staff.user, outsider.user):
        with pytest.raises(BrainAccessDenied) as denied:
            _admit(user, establishment, reporting, key="privee")
        assert denied.value.code == "brain_access_denied"
    assert BrainAnalysis.objects.get().id == analysis.id


def test_two_establishments_can_each_hold_a_slot(settings):
    settings.HOUSTON_BRAIN_MAX_QUEUED_AND_RUNNING = 2
    first = create_establishment(name="Hotel un")
    second = create_establishment(name="Hotel deux")
    owner_a = create_membership(establishment=first, role=EstablishmentMembership.Role.OWNER)
    owner_b = create_membership(establishment=second, role=EstablishmentMembership.Role.DIRECTOR)
    reporting_a = _reporting(first, owner_a.user)
    reporting_b = _reporting(second, owner_b.user)
    _admit(owner_a.user, first, reporting_a, key="a")
    _admit(owner_b.user, second, reporting_b, key="a")
    assert BrainSlot.objects.filter(status=BrainSlot.Status.QUEUED).count() == 2


def test_admitted_configuration_does_not_follow_later_setting_changes(settings):
    settings.HOUSTON_BRAIN_CAPTURE_TIMEOUT_SECONDS = 20
    establishment = create_establishment(name="Brain config")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    reporting = _reporting(establishment, owner.user)
    analysis = _admit(owner.user, establishment, reporting)
    settings.HOUSTON_BRAIN_CAPTURE_TIMEOUT_SECONDS = 1
    analysis.refresh_from_db()
    assert analysis.configuration["ceilings"]["capture_timeout_seconds"] == 20


def test_a_second_request_returns_the_active_work_instead_of_inserting_another():
    establishment = create_establishment(name="Brain active")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    reporting = _reporting(establishment, owner.user)
    first = _admit(owner.user, establishment, reporting, key="une")
    second = _admit(owner.user, establishment, reporting, key="deux")
    assert second.id == first.id
    assert BrainAnalysis.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_admissions_for_one_establishment_insert_one_analysis():
    establishment = create_establishment(name="Brain race")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    reporting = _reporting(establishment, owner.user)

    def admit(key):
        try:
            return admit_brain_work(
                user=owner.user,
                establishment_id=establishment.id,
                reporting_id=reporting.id,
                idempotency_key=key,
            ).id
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(admit, ("course-a", "course-b")))
    assert results[0] == results[1]
    assert BrainAnalysis.objects.filter(establishment=establishment).count() == 1
    assert BrainSlot.objects.filter(establishment=establishment).count() == 1


@pytest.mark.django_db(transaction=True)
def test_two_establishments_racing_for_the_last_slot_admit_one(settings):
    settings.HOUSTON_BRAIN_MAX_QUEUED_AND_RUNNING = 1
    first = create_establishment(name="Brain dernier un")
    second = create_establishment(name="Brain dernier deux")
    owner_a = create_membership(establishment=first, role=EstablishmentMembership.Role.OWNER)
    owner_b = create_membership(establishment=second, role=EstablishmentMembership.Role.DIRECTOR)
    reporting_a = _reporting(first, owner_a.user)
    reporting_b = _reporting(second, owner_b.user)

    def admit(args):
        owner, establishment, reporting = args
        try:
            analysis = admit_brain_work(
                user=owner.user,
                establishment_id=establishment.id,
                reporting_id=reporting.id,
                idempotency_key="dernier-creneau",
            )
            return analysis.id
        except BrainCapacityUnavailable:
            return None
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                admit,
                (
                    (owner_a, first, reporting_a),
                    (owner_b, second, reporting_b),
                ),
            )
        )
    admitted = [analysis_id for analysis_id in results if analysis_id is not None]
    assert len(admitted) == 1
    assert results.count(None) == 1
    assert BrainAnalysis.objects.count() == 1
    assert BrainSlot.objects.count() == 1
    assert admitted[0] == BrainAnalysis.objects.get().id


def test_director_of_the_establishment_can_admit():
    establishment = create_establishment(name="Brain director")
    director = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    reporting = _reporting(establishment, director.user)
    analysis = _admit(director.user, establishment, reporting)
    assert analysis.establishment_id == establishment.id


def test_reporting_from_another_establishment_is_not_admitted():
    home = create_establishment(name="Brain home")
    other = create_establishment(name="Brain other reporting")
    owner = create_membership(establishment=home, role=EstablishmentMembership.Role.OWNER)
    foreign = create_membership(establishment=other, role=EstablishmentMembership.Role.OWNER)
    reporting = _reporting(other, foreign.user)
    with pytest.raises(BrainWorkError) as refused:
        _admit(owner.user, home, reporting)
    assert refused.value.code == "reporting_not_ready"
    assert BrainAnalysis.objects.count() == 0
