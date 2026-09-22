from __future__ import annotations

import io
from datetime import timedelta

import pytest
from django.db import transaction
from django.utils import timezone
from PIL import Image

from houston.action_plans.constants import (
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.action_plans.services import (
    _cancel_linked_active_executions_for_signal_resolve,
    cancel_action_plan_execution,
    create_action_plan_with_execution,
    mark_action_plan_execution_done,
    reopen_action_plan_execution,
)
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.comments.constants import (
    ATTACHMENT_TOO_LARGE_ERROR_DETAIL,
    ATTACHMENTS_NOT_ALLOWED_ERROR_DETAIL,
)
from houston.comments.models import ActionPlanCommentAttachment, ActionPlanCommentUpload
from houston.comments.services import create_action_plan_execution_comment, create_signal_comment
from houston.comments.tests.conftest import (
    auth_headers,
    build_api_membership,
    execution_comments_url,
    login,
    signal_comments_url,
)
from houston.comments.upload_services import (
    cleanup_expired_action_plan_comment_retention,
    cleanup_expired_action_plan_comment_uploads,
    complete_action_plan_comment_upload,
    reserve_action_plan_comment_upload,
    store_action_plan_comment_upload_content,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup
from houston.uploads.private_storage import get_action_plan_comment_private_media_storage

pytestmark = pytest.mark.django_db


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color=(12, 80, 160)).save(buffer, format="PNG")
    return buffer.getvalue()


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _setup_execution(*, requires_validation=True):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, _electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Attachment execution",
        requires_validation=requires_validation,
        tasks=[build_task_payload(task="Inspect", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )
    return owner, staff, execution


def _upload_urls(establishment_id, execution_id, suffix=""):
    base = (
        f"/api/v1/establishments/{establishment_id}/action-plan-executions/"
        f"{execution_id}/comment-uploads/"
    )
    return f"{base}{suffix}"


def _preview_url(establishment_id, execution_id, attachment_id):
    return (
        f"/api/v1/establishments/{establishment_id}/action-plan-executions/"
        f"{execution_id}/comment-attachments/{attachment_id}/preview/"
    )


def _reserve_put_complete(
    api_client,
    *,
    token,
    establishment_id,
    execution_id,
    filename="note.png",
    content_type="image/png",
    payload=None,
):
    payload = payload if payload is not None else _png_bytes()
    reserve = api_client.post(
        _upload_urls(establishment_id, execution_id),
        {
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(payload),
        },
        format="json",
        **auth_headers(token),
    )
    assert reserve.status_code == 201, reserve.content
    upload_id = reserve.json()["upload_id"]
    put = api_client.put(
        _upload_urls(establishment_id, execution_id, f"{upload_id}/content/"),
        data=payload,
        content_type="application/octet-stream",
        **auth_headers(token),
    )
    assert put.status_code == 204, put.content
    complete = api_client.post(
        _upload_urls(establishment_id, execution_id, f"{upload_id}/complete/"),
        **auth_headers(token),
    )
    assert complete.status_code == 200, complete.content
    return upload_id, complete.json()


def test_publish_comment_with_image_and_pdf(api_client, settings, tmp_path):
    settings.HOUSTON_ACTION_PLAN_PRIVATE_MEDIA_ROOT = str(tmp_path)
    owner, staff, execution = _setup_execution()
    token = login(api_client, user=staff.user)
    png_id, _ = _reserve_put_complete(
        api_client,
        token=token,
        establishment_id=staff.establishment_id,
        execution_id=execution.id,
    )
    pdf_id, complete = _reserve_put_complete(
        api_client,
        token=token,
        establishment_id=staff.establishment_id,
        execution_id=execution.id,
        filename="report.pdf",
        content_type="application/pdf",
        payload=_pdf_bytes(),
    )
    assert complete["kind"] == "document"

    created = api_client.post(
        execution_comments_url(staff.establishment_id, execution.id),
        {"body": "Preuves terrain", "attachment_ids": [png_id, pdf_id]},
        format="json",
        **auth_headers(token),
    )
    assert created.status_code == 201, created.content
    attachments = created.json()["attachments"]
    assert len(attachments) == 2
    assert attachments[0]["kind"] == "image"
    assert attachments[1]["kind"] == "document"
    assert attachments[0]["comment_id"] == created.json()["id"]

    listed = api_client.get(
        execution_comments_url(staff.establishment_id, execution.id),
        **auth_headers(token),
    )
    assert listed.status_code == 200
    thread = listed.json()[0]
    assert thread["attachments"][0]["original_filename"] == "note.png"
    preview = api_client.get(
        attachments[0]["preview_url"],
        **auth_headers(token),
    )
    assert preview.status_code == 200


def test_reply_can_carry_attachments(api_client, settings, tmp_path):
    settings.HOUSTON_ACTION_PLAN_PRIVATE_MEDIA_ROOT = str(tmp_path)
    owner, staff, execution = _setup_execution()
    token = login(api_client, user=staff.user)
    root = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="root",
    )
    upload_id, _ = _reserve_put_complete(
        api_client,
        token=token,
        establishment_id=staff.establishment_id,
        execution_id=execution.id,
    )
    reply = api_client.post(
        execution_comments_url(staff.establishment_id, execution.id),
        {
            "body": "reply with file",
            "parent_comment_id": str(root.id),
            "attachment_ids": [upload_id],
        },
        format="json",
        **auth_headers(token),
    )
    assert reply.status_code == 201
    assert len(reply.json()["attachments"]) == 1


@pytest.mark.parametrize(
    "status",
    [EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_DONE, EXECUTION_STATUS_CANCELED],
)
def test_reserve_refused_outside_active_statuses(api_client, settings, tmp_path, status):
    settings.HOUSTON_ACTION_PLAN_PRIVATE_MEDIA_ROOT = str(tmp_path)
    owner, staff, execution = _setup_execution()
    execution.status = status
    execution.save(update_fields=["status", "updated_at"])
    token = login(api_client, user=staff.user)
    payload = _png_bytes()
    response = api_client.post(
        _upload_urls(staff.establishment_id, execution.id),
        {
            "filename": "note.png",
            "content_type": "image/png",
            "size_bytes": len(payload),
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == ATTACHMENTS_NOT_ALLOWED_ERROR_DETAIL


def test_status_race_refuses_link_and_keeps_text_unpublished(api_client, settings, tmp_path):
    settings.HOUSTON_ACTION_PLAN_PRIVATE_MEDIA_ROOT = str(tmp_path)
    owner, staff, execution = _setup_execution()
    token = login(api_client, user=staff.user)
    upload_id, _ = _reserve_put_complete(
        api_client,
        token=token,
        establishment_id=staff.establishment_id,
        execution_id=execution.id,
    )
    execution.status = EXECUTION_STATUS_DONE
    execution.marked_done_at = timezone.now()
    execution.save(update_fields=["status", "marked_done_at", "updated_at"])
    created = api_client.post(
        execution_comments_url(staff.establishment_id, execution.id),
        {"body": "still want this text", "attachment_ids": [upload_id]},
        format="json",
        **auth_headers(token),
    )
    assert created.status_code == 400
    assert created.json()["detail"] == ATTACHMENTS_NOT_ALLOWED_ERROR_DETAIL
    listed = api_client.get(
        execution_comments_url(staff.establishment_id, execution.id),
        **auth_headers(token),
    )
    assert listed.json() == []


def test_text_only_comment_still_allowed_when_done(api_client):
    owner, staff, execution = _setup_execution()
    execution.status = EXECUTION_STATUS_DONE
    execution.marked_done_at = timezone.now()
    execution.save(update_fields=["status", "marked_done_at", "updated_at"])
    token = login(api_client, user=staff.user)
    created = api_client.post(
        execution_comments_url(staff.establishment_id, execution.id),
        {"body": "suivi sans fichier"},
        format="json",
        **auth_headers(token),
    )
    assert created.status_code == 201
    assert created.json().get("attachments") == []


def test_unsupported_type_and_oversize(api_client, settings, tmp_path):
    settings.HOUSTON_ACTION_PLAN_PRIVATE_MEDIA_ROOT = str(tmp_path)
    owner, staff, execution = _setup_execution()
    token = login(api_client, user=staff.user)
    too_big = api_client.post(
        _upload_urls(staff.establishment_id, execution.id),
        {
            "filename": "huge.png",
            "content_type": "image/png",
            "size_bytes": 11 * 1024 * 1024,
        },
        format="json",
        **auth_headers(token),
    )
    assert too_big.status_code == 400
    assert too_big.json()["detail"] == ATTACHMENT_TOO_LARGE_ERROR_DETAIL

    reserve = api_client.post(
        _upload_urls(staff.establishment_id, execution.id),
        {
            "filename": "note.txt",
            "content_type": "text/plain",
            "size_bytes": 4,
        },
        format="json",
        **auth_headers(token),
    )
    upload_id = reserve.json()["upload_id"]
    api_client.put(
        _upload_urls(staff.establishment_id, execution.id, f"{upload_id}/content/"),
        data=b"nope",
        content_type="application/octet-stream",
        **auth_headers(token),
    )
    complete = api_client.post(
        _upload_urls(staff.establishment_id, execution.id, f"{upload_id}/complete/"),
        **auth_headers(token),
    )
    assert complete.status_code == 400
    assert complete.json()["detail"] == "Le contenu du fichier est invalide."


def test_cannot_use_someone_elses_upload(api_client, settings, tmp_path):
    settings.HOUSTON_ACTION_PLAN_PRIVATE_MEDIA_ROOT = str(tmp_path)
    owner, staff, execution = _setup_execution()
    staff_token = login(api_client, user=staff.user)
    upload_id, _ = _reserve_put_complete(
        api_client,
        token=staff_token,
        establishment_id=staff.establishment_id,
        execution_id=execution.id,
    )
    owner_token = login(api_client, user=owner.user)
    created = api_client.post(
        execution_comments_url(owner.establishment_id, execution.id),
        {"body": "steal", "attachment_ids": [upload_id]},
        format="json",
        **auth_headers(owner_token),
    )
    assert created.status_code == 400


def test_without_plan_access_cannot_preview(api_client, settings, tmp_path):
    settings.HOUSTON_ACTION_PLAN_PRIVATE_MEDIA_ROOT = str(tmp_path)
    owner, staff, execution = _setup_execution()
    outsider = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    token = login(api_client, user=staff.user)
    upload_id, _ = _reserve_put_complete(
        api_client,
        token=token,
        establishment_id=staff.establishment_id,
        execution_id=execution.id,
    )
    created = api_client.post(
        execution_comments_url(staff.establishment_id, execution.id),
        {"body": "preuve", "attachment_ids": [upload_id]},
        format="json",
        **auth_headers(token),
    )
    outsider_token = login(api_client, user=outsider.user)
    preview = api_client.get(
        created.json()["attachments"][0]["preview_url"],
        **auth_headers(outsider_token),
    )
    assert preview.status_code == 404


def test_signal_comments_remain_without_attachments(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    create_signal_comment(author_membership=owner, signal=signal, body="signal only")
    token = login(api_client, user=owner.user)
    response = api_client.get(
        signal_comments_url(owner.establishment_id, signal.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert "attachments" not in response.json()[0]


@pytest.mark.django_db(transaction=True)
def test_cancel_purges_storage_immediately(settings, tmp_path):
    settings.HOUSTON_ACTION_PLAN_PRIVATE_MEDIA_ROOT = str(tmp_path)
    owner, staff, execution = _setup_execution()
    payload = _png_bytes()
    upload = reserve_action_plan_comment_upload(
        actor_membership=staff,
        execution=execution,
        original_filename="note.png",
        content_type="image/png",
        size_bytes=len(payload),
    )
    store_action_plan_comment_upload_content(upload=upload, payload=payload)
    complete_action_plan_comment_upload(
        actor_membership=staff,
        execution=execution,
        upload_id=upload.id,
    )
    create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="with file",
        attachment_ids=[upload.id],
    )
    storage = get_action_plan_comment_private_media_storage()
    assert storage.exists(upload.storage_key)
    cancel_action_plan_execution(execution_id=execution.id, actor=owner)
    assert ActionPlanCommentAttachment.objects.filter(
        action_plan_execution_id=execution.id
    ).count() == 0
    remaining_uploads = ActionPlanCommentUpload.objects.filter(
        action_plan_execution_id=execution.id
    ).count()
    assert remaining_uploads == 0
    assert not storage.exists(upload.storage_key)


@pytest.mark.django_db(transaction=True)
def test_signal_resolve_cascade_purges_attachments(settings, tmp_path):
    settings.HOUSTON_ACTION_PLAN_PRIVATE_MEDIA_ROOT = str(tmp_path)
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Linked",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Inspect", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )
    payload = _png_bytes()
    upload = reserve_action_plan_comment_upload(
        actor_membership=staff,
        execution=execution,
        original_filename="note.png",
        content_type="image/png",
        size_bytes=len(payload),
    )
    store_action_plan_comment_upload_content(upload=upload, payload=payload)
    complete_action_plan_comment_upload(
        actor_membership=staff,
        execution=execution,
        upload_id=upload.id,
    )
    create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="linked file",
        attachment_ids=[upload.id],
    )
    with transaction.atomic():
        _cancel_linked_active_executions_for_signal_resolve(signal=signal)
    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_CANCELED
    assert ActionPlanCommentAttachment.objects.filter(
        action_plan_execution_id=execution.id
    ).count() == 0


def test_done_available_then_retention_purge(api_client, settings, tmp_path):
    settings.HOUSTON_ACTION_PLAN_PRIVATE_MEDIA_ROOT = str(tmp_path)
    owner, staff, execution = _setup_execution(requires_validation=False)
    token = login(api_client, user=staff.user)
    upload_id, _ = _reserve_put_complete(
        api_client,
        token=token,
        establishment_id=staff.establishment_id,
        execution_id=execution.id,
    )
    created = api_client.post(
        execution_comments_url(staff.establishment_id, execution.id),
        {"body": "cloture", "attachment_ids": [upload_id]},
        format="json",
        **auth_headers(token),
    )
    attachment_id = created.json()["attachments"][0]["id"]
    mark_action_plan_execution_done(execution_id=execution.id, actor_membership=staff)
    preview = api_client.get(
        _preview_url(staff.establishment_id, execution.id, attachment_id),
        **auth_headers(token),
    )
    assert preview.status_code == 200
    execution.refresh_from_db()
    execution.marked_done_at = timezone.now() - timedelta(days=31)
    execution.save(update_fields=["marked_done_at", "updated_at"])
    listed = api_client.get(
        execution_comments_url(staff.establishment_id, execution.id),
        **auth_headers(token),
    )
    assert listed.json()[0]["attachments"] == []
    preview_after = api_client.get(
        _preview_url(staff.establishment_id, execution.id, attachment_id),
        **auth_headers(token),
    )
    assert preview_after.status_code == 404
    cleanup_expired_action_plan_comment_retention()
    assert ActionPlanCommentAttachment.objects.filter(id=attachment_id).count() == 0


def test_reopen_from_pending_validation_keeps_files_and_allows_add(api_client, settings, tmp_path):
    settings.HOUSTON_ACTION_PLAN_PRIVATE_MEDIA_ROOT = str(tmp_path)
    owner, staff, execution = _setup_execution(requires_validation=True)
    token = login(api_client, user=staff.user)
    upload_id, _ = _reserve_put_complete(
        api_client,
        token=token,
        establishment_id=staff.establishment_id,
        execution_id=execution.id,
    )
    created = api_client.post(
        execution_comments_url(staff.establishment_id, execution.id),
        {"body": "avant reopen", "attachment_ids": [upload_id]},
        format="json",
        **auth_headers(token),
    )
    mark_action_plan_execution_done(execution_id=execution.id, actor_membership=staff)
    reopen_action_plan_execution(execution_id=execution.id, actor=owner)
    listed = api_client.get(
        execution_comments_url(staff.establishment_id, execution.id),
        **auth_headers(token),
    )
    assert listed.json()[0]["attachments"][0]["id"] == created.json()["attachments"][0]["id"]
    extra_id, _ = _reserve_put_complete(
        api_client,
        token=token,
        establishment_id=staff.establishment_id,
        execution_id=execution.id,
        filename="after.png",
    )
    after = api_client.post(
        execution_comments_url(staff.establishment_id, execution.id),
        {"body": "apres reopen", "attachment_ids": [extra_id]},
        format="json",
        **auth_headers(token),
    )
    assert after.status_code == 201


@pytest.mark.django_db(transaction=True)
def test_orphan_uploads_are_cleaned(settings, tmp_path):
    settings.HOUSTON_ACTION_PLAN_PRIVATE_MEDIA_ROOT = str(tmp_path)
    owner, staff, execution = _setup_execution()
    payload = _png_bytes()
    upload = reserve_action_plan_comment_upload(
        actor_membership=staff,
        execution=execution,
        original_filename="orphan.png",
        content_type="image/png",
        size_bytes=len(payload),
    )
    store_action_plan_comment_upload_content(upload=upload, payload=payload)
    ActionPlanCommentUpload.objects.filter(id=upload.id).update(
        expires_at=timezone.now() - timedelta(hours=1)
    )
    deleted = cleanup_expired_action_plan_comment_uploads()
    assert deleted == 1
    assert ActionPlanCommentUpload.objects.filter(id=upload.id).count() == 0
    storage = get_action_plan_comment_private_media_storage()
    assert not storage.exists(upload.storage_key)


def test_inherited_signal_comments_have_no_plan_attachments(api_client, settings, tmp_path):
    settings.HOUSTON_ACTION_PLAN_PRIVATE_MEDIA_ROOT = str(tmp_path)
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Linked",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Inspect", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )
    create_signal_comment(author_membership=owner, signal=signal, body="signal note")
    token = login(api_client, user=staff.user)
    listed = api_client.get(
        execution_comments_url(staff.establishment_id, execution.id),
        **auth_headers(token),
    )
    inherited = next(item for item in listed.json() if item["item_type"] == "inherited_signal")
    assert "attachments" not in inherited
