from __future__ import annotations

import uuid
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

from houston.accounts.models import User
from houston.analytics.models import (
    AnalyticsHistoryCoverage,
    OperationalPattern,
    PatternEstablishmentSighting,
    PatternIssueReport,
    PatternLifecycleEvent,
)
from houston.analytics.services import create_operational_pattern
from houston.comments.models import Comment
from houston.core.dev_guards import LocalDevEnvironmentError, assert_local_dev_environment
from houston.core.operational_test_data_cleanup import clean_operational_test_data
from houston.establishments.models import (
    BusinessUnit,
    CatalogBusinessUnit,
    Establishment,
    EstablishmentMembership,
)
from houston.gamification.constants import BADGE_CODE_BRONZE, CURRENT_RULE_VERSION
from houston.gamification.models import BadgeAward, GamificationSeason, PointTransaction
from houston.gamification.services import open_season
from houston.notifications.models import Notification
from houston.notifications.tests.conftest import create_test_notification
from houston.observations.models import Observation, ObservationMedia, ObservationProcessing
from houston.signals.models import Signal
from houston.testing.factories import build_membership
from houston.testing.pipeline import create_observation
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup
from houston.uploads.models import TemporaryUpload

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


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_assert_local_dev_environment_accepts_local_postgres_host():
    assert_local_dev_environment()


REMOTE_DATABASES = {
    **LOCAL_DATABASES,
    "default": {**LOCAL_DATABASES["default"], "HOST": "neon.example.com"},
}


@override_settings(DEBUG=True, DATABASES=REMOTE_DATABASES)
def test_assert_local_dev_environment_rejects_remote_host():
    with pytest.raises(LocalDevEnvironmentError, match="neon.example.com"):
        assert_local_dev_environment()


@override_settings(DEBUG=False, DATABASES=LOCAL_DATABASES)
def test_assert_local_dev_environment_requires_debug():
    with pytest.raises(LocalDevEnvironmentError, match="DJANGO_DEBUG"):
        assert_local_dev_environment()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_command_requires_confirm_without_dry_run():
    with pytest.raises(CommandError, match="--confirm"):
        call_command("clean_operational_test_data")


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_dry_run_does_not_delete_rows():
    membership = build_membership()
    create_observation(membership=membership)
    create_test_notification(recipient=membership)

    result = clean_operational_test_data(dry_run=True)

    assert result.dry_run is True
    assert result.counts.observations >= 1
    assert Observation.objects.exists()
    assert Notification.objects.exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
@patch("houston.core.operational_test_data_cleanup.schedule_storage_files_deletion")
def test_dry_run_does_not_schedule_media_deletion(mock_schedule):
    membership = build_membership()
    create_observation(membership=membership)

    clean_operational_test_data(dry_run=True)

    mock_schedule.assert_not_called()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
@patch("houston.core.operational_test_data_cleanup.schedule_storage_files_deletion")
def test_confirm_schedules_media_deletion_after_db_work(mock_schedule):
    membership = build_membership()
    observation = create_observation(membership=membership)
    upload = _create_linked_upload(membership=membership, observation=observation)

    clean_operational_test_data(dry_run=False)

    mock_schedule.assert_called_once()
    storage_keys = mock_schedule.call_args.kwargs["storage_keys"]
    assert upload.file.name in storage_keys
    assert not Observation.objects.filter(id=observation.id).exists()
    assert not TemporaryUpload.objects.filter(id=upload.id).exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_confirm_preserves_tenancy_and_catalog_infra():
    membership = build_membership()
    hotel, maintenance_bu, electricite = hotel_maintenance_setup(membership.establishment)
    catalog = CatalogBusinessUnit.objects.create(
        key=f"test-catalog-{uuid.uuid4().hex[:8]}",
        label="Test Catalog BU",
    )
    create_observation(membership=membership)
    create_test_notification(recipient=membership)
    signal = create_signal_v3_for_membership(
        membership,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance_bu,
        activity_subject=electricite,
    )
    Comment.objects.create(
        establishment=membership.establishment,
        signal=signal,
        author_membership=membership,
        body="Test comment",
    )

    user_id = membership.user_id
    establishment_id = membership.establishment_id
    membership_id = membership.id
    business_unit_id = maintenance_bu.id
    catalog_id = catalog.id

    clean_operational_test_data(dry_run=False)

    assert User.objects.filter(id=user_id).exists()
    assert Establishment.objects.filter(id=establishment_id).exists()
    assert EstablishmentMembership.objects.filter(id=membership_id).exists()
    assert BusinessUnit.objects.filter(id=business_unit_id).exists()
    assert CatalogBusinessUnit.objects.filter(id=catalog_id).exists()
    assert not Observation.objects.exists()
    assert not Notification.objects.exists()
    assert not Signal.objects.exists()
    assert not Comment.objects.exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_command_dry_run_stdout_summary():
    membership = build_membership()
    create_observation(membership=membership)

    stdout = StringIO()
    call_command("clean_operational_test_data", "--dry-run", stdout=stdout)

    output = stdout.getvalue()
    assert "Dry run" in output
    assert "catalog_infra" in output
    assert "ActionPlan templates" in output
    assert Observation.objects.exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_dry_run_does_not_change_analytics_or_points_or_coverage():
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    _seed_pattern_chain_and_points(membership)
    old_reliable_from = timezone.now() - timedelta(days=40)
    AnalyticsHistoryCoverage.objects.update_or_create(
        singleton_key=AnalyticsHistoryCoverage.SINGLETON_KEY,
        defaults={"reliable_from": old_reliable_from},
    )

    result = clean_operational_test_data(dry_run=True)

    assert result.history_reliable_from is None
    assert result.counts.operational_patterns >= 3
    assert result.counts.point_transactions >= 2
    assert OperationalPattern.objects.count() >= 3
    assert PointTransaction.objects.exists()
    assert BadgeAward.objects.exists()
    assert AnalyticsHistoryCoverage.objects.get().reliable_from == old_reliable_from


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_confirm_clears_pattern_chains_points_and_resets_coverage():
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    hotel, maintenance_bu, electricite = hotel_maintenance_setup(membership.establishment)
    create_signal_v3_for_membership(
        membership,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance_bu,
        activity_subject=electricite,
    )
    season = _seed_pattern_chain_and_points(membership)
    old_reliable_from = timezone.now() - timedelta(days=40)
    AnalyticsHistoryCoverage.objects.update_or_create(
        singleton_key=AnalyticsHistoryCoverage.SINGLETON_KEY,
        defaults={"reliable_from": old_reliable_from},
    )
    before = timezone.now()

    result = clean_operational_test_data(dry_run=False)

    assert result.history_reliable_from is not None
    assert result.history_reliable_from >= before
    assert result.history_reliable_from != old_reliable_from
    assert AnalyticsHistoryCoverage.objects.get().reliable_from == result.history_reliable_from
    assert not Signal.objects.exists()
    assert not OperationalPattern.objects.exists()
    assert not PatternEstablishmentSighting.objects.exists()
    assert not PatternIssueReport.objects.exists()
    assert not PatternLifecycleEvent.objects.exists()
    assert not PointTransaction.objects.exists()
    assert not BadgeAward.objects.exists()
    assert GamificationSeason.objects.filter(pk=season.pk).exists()
    assert EstablishmentMembership.objects.filter(pk=membership.pk).exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_confirm_counts_match_dry_run_named_model_rows():
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    hotel, maintenance_bu, electricite = hotel_maintenance_setup(membership.establishment)
    create_signal_v3_for_membership(
        membership,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance_bu,
        activity_subject=electricite,
    )
    _seed_pattern_chain_and_points(membership)
    expected_signals = Signal.objects.count()
    expected_patterns = OperationalPattern.objects.count()
    expected_events = PatternLifecycleEvent.objects.count()
    expected_sightings = PatternEstablishmentSighting.objects.count()
    expected_reports = PatternIssueReport.objects.count()
    expected_points = PointTransaction.objects.count()
    expected_badges = BadgeAward.objects.count()

    dry_run = clean_operational_test_data(dry_run=True)
    confirmed = clean_operational_test_data(dry_run=False)

    assert confirmed.counts == dry_run.counts
    assert confirmed.counts.signals == expected_signals
    assert confirmed.counts.operational_patterns == expected_patterns
    assert confirmed.counts.pattern_lifecycle_events == expected_events
    assert confirmed.counts.pattern_sightings == expected_sightings
    assert confirmed.counts.pattern_issue_reports == expected_reports
    assert confirmed.counts.point_transactions == expected_points
    assert confirmed.counts.badge_awards == expected_badges
    assert confirmed.counts.signals == 1
    assert confirmed.counts.operational_patterns == 3
    assert confirmed.counts.point_transactions == 2
    assert confirmed.counts.badge_awards == 1
    assert not Signal.objects.exists()
    assert not OperationalPattern.objects.exists()


COMMAND_REMOTE_DATABASES = {
    **LOCAL_DATABASES,
    "default": {**LOCAL_DATABASES["default"], "HOST": "remote.db.example.com"},
}


@override_settings(DEBUG=True, DATABASES=COMMAND_REMOTE_DATABASES)
def test_command_maps_local_dev_guard_to_command_error():
    with pytest.raises(CommandError, match="remote.db.example.com"):
        call_command("clean_operational_test_data", "--dry-run")


def _seed_pattern_chain_and_points(membership):
    organization = membership.establishment.organization
    leaf = create_operational_pattern(
        organization=organization,
        label="Leaf motif",
        created_by_membership=membership,
    )
    mid = create_operational_pattern(
        organization=organization,
        label="Mid motif",
        created_by_membership=membership,
    )
    root = create_operational_pattern(
        organization=organization,
        label="Root motif",
        created_by_membership=membership,
    )
    OperationalPattern.objects.filter(pk=leaf.pk).update(
        status=OperationalPattern.Status.MERGED,
        merged_into=mid,
    )
    OperationalPattern.objects.filter(pk=mid.pk).update(
        status=OperationalPattern.Status.MERGED,
        merged_into=root,
    )
    PatternEstablishmentSighting.objects.create(
        pattern=root,
        establishment=membership.establishment,
        observed_at=timezone.now(),
    )
    PatternIssueReport.objects.create(
        pattern=root,
        organization=organization,
        reported_by_membership=membership,
        report_type="duplicate",
    )
    season = open_season(membership.establishment)
    original_id = uuid.uuid4()
    original = PointTransaction.objects.create(
        id=original_id,
        membership=membership,
        establishment=membership.establishment,
        season=season,
        delta=5,
        reason_code="test.award",
        source_type="test",
        source_id=str(original_id),
        rule_version=CURRENT_RULE_VERSION,
        occurred_at=timezone.now(),
        idempotency_key=f"tx:{original_id}",
    )
    reversal_id = uuid.uuid4()
    PointTransaction.objects.create(
        id=reversal_id,
        membership=membership,
        establishment=membership.establishment,
        season=season,
        delta=-5,
        reason_code="test.reversal",
        source_type="test",
        source_id=str(reversal_id),
        rule_version=CURRENT_RULE_VERSION,
        occurred_at=timezone.now(),
        idempotency_key=f"tx:{reversal_id}",
        reversed_transaction=original,
    )
    BadgeAward.objects.create(
        membership=membership,
        establishment=membership.establishment,
        season=season,
        badge_code=BADGE_CODE_BRONZE,
        points_total=30,
        awarded_at=timezone.now(),
    )
    return season


def _create_linked_upload(*, membership, observation: Observation) -> TemporaryUpload:
    upload = TemporaryUpload(
        establishment=membership.establishment,
        uploaded_by=membership.user,
        content_type="image/png",
        stored_extension="png",
        size_bytes=4,
        status=TemporaryUpload.Status.LINKED,
        expires_at=timezone.now() + timedelta(hours=1),
        linked_at=timezone.now(),
    )
    upload.file.save(
        "photo.png",
        SimpleUploadedFile("photo.png", b"\x89PNG\r\n\x1a\n", content_type="image/png"),
        save=False,
    )
    upload.save()
    ObservationMedia.objects.create(
        observation=observation,
        temporary_upload=upload,
        position=1,
        content_type=upload.content_type,
        size_bytes=upload.size_bytes,
        storage_key=upload.file.name,
    )
    ObservationProcessing.objects.get(observation=observation)
    return upload
