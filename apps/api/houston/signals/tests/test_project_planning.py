from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

from houston.comments.models import ActionPlanCommentAttachment, ActionPlanCommentUpload, Comment
from houston.signals.exceptions import (
    SignalPermissionError,
    SignalStateError,
    SignalValidationError,
)
from houston.signals.planning_services import schedule_record, set_record_predecessor
from houston.signals.project_services import organize_record
from houston.signals.record_documents import record_documents
from houston.signals.record_selectors import calendar_dates, get_record, record_queryset
from houston.signals.record_services import create_record
from houston.signals.tests.test_field_records import change, work
from houston.testing.auth import (
    assign_business_unit_scope,
    auth_headers,
    build_api_membership,
    build_api_membership_on_establishment,
    login,
)
from houston.testing.taxonomy import create_minimal_v3_signal

pytestmark = pytest.mark.django_db


@pytest.fixture
def context():
    owner = build_api_membership(role="owner")
    source = create_minimal_v3_signal(owner)
    return owner, source


def make(context, title="Nouvelle implantation", **kwargs):
    owner, source = context
    return create_record(
        actor=owner, title=title, business_unit_id=source.responsible_business_unit_id, **kwargs
    )


def plan(owner, record, start=1, end=3, *, apply=False, versions=None):
    record.refresh_from_db()
    today = timezone.localdate()
    return schedule_record(
        actor=owner,
        record_id=record.id,
        expected_updated_at=record.updated_at,
        start_on=today + timedelta(days=start),
        due_on=today + timedelta(days=end),
        apply=apply,
        expected_versions=versions,
    )


def dated(context, title, start, end):
    r = make(context, title=title)
    preview = plan(context[0], r, start, end)
    plan(context[0], r, start, end, apply=True, versions=preview["versions"])
    r.refresh_from_db()
    return r


def depend(owner, child, previous):
    child.refresh_from_db()
    return set_record_predecessor(
        actor=owner,
        record_id=child.id,
        expected_updated_at=child.updated_at,
        predecessor_id=previous.id if previous else None,
    )


def test_project_hierarchy_keeps_records_and_accessible_progress(context):
    owner, _ = context
    project = make(context, is_project=True)
    sub = make(context, is_project=True, parent_project_id=project.id)
    child = make(context, parent_project_id=sub.id)
    assert not project.source_observation_links.exists()
    assert get_record(owner, project.id).visible_child_count == 1
    with pytest.raises(SignalStateError):
        change(owner, sub, stage="closed", closure_reason="acknowledged")
    change(owner, child, stage="closed", closure_reason="acknowledged")
    assert get_record(owner, sub.id).visible_closed_child_count == 1
    sub.refresh_from_db()
    assert sub.status != "resolved"
    change(owner, sub, stage="closed", closure_reason="acknowledged")
    assert get_record(owner, project.id).visible_closed_child_count == 1


def test_project_rejects_cycles_depth_and_demoting_parent(context):
    owner, _ = context
    top = make(context, is_project=True)
    sub = make(context, is_project=True, parent_project_id=top.id)
    low = make(context, is_project=True, parent_project_id=sub.id)
    with pytest.raises(SignalValidationError):
        make(context, parent_project_id=low.id)
    for parent, project in ((sub.id, True), (None, False)):
        top.refresh_from_db()
        with pytest.raises(SignalValidationError):
            organize_record(
                actor=owner,
                record_id=top.id,
                expected_updated_at=top.updated_at,
                parent_project_id=parent,
                is_project=project,
            )
    assert top.parent_project_id is None


def test_existing_observation_can_join_but_not_become_project(context):
    owner, source = context
    project = make(context, is_project=True)
    organize_record(
        actor=owner,
        record_id=source.id,
        expected_updated_at=source.updated_at,
        parent_project_id=project.id,
    )
    source.refresh_from_db()
    assert source.parent_project_id == project.id
    with pytest.raises(SignalValidationError):
        organize_record(
            actor=owner, record_id=source.id, expected_updated_at=source.updated_at, is_project=True
        )


def test_project_does_not_broaden_staff_visibility(context):
    owner, source = context
    staff = build_api_membership_on_establishment(owner, role="staff")
    assign_business_unit_scope(staff, source.responsible_business_unit)
    project = make(context, is_project=True, owner_membership_id=staff.id)
    hidden = make(context, parent_project_id=project.id)
    assert get_record(staff, project.id).visible_child_count == 0
    assert get_record(staff, hidden.id) is None
    assert get_record(owner, project.id).visible_child_count == 1


def test_foreign_project_is_never_accepted(context):
    foreign = build_api_membership(role="owner")
    other_source = create_minimal_v3_signal(foreign)
    project = make((foreign, other_source), is_project=True)
    with pytest.raises(SignalValidationError):
        make(context, parent_project_id=project.id)


def test_preview_then_cascade_keeps_creation_and_execution_dates(context):
    owner, _ = context
    first = dated(context, "Conception", 1, 3)
    second = dated(context, "Installation", 4, 6)
    third = dated(context, "Ouverture", 7, 7)
    depend(owner, second, first)
    depend(owner, third, second)
    execution = work(owner, second, ["Installer le mobilier"])
    execution_due = execution.end_at
    created = first.created_at
    preview = plan(owner, first, 3, 5)
    assert len(preview["changes"]) == 3 and not preview["applied"]
    first.refresh_from_db()
    assert first.due_on == timezone.localdate() + timedelta(days=3)
    result = plan(owner, first, 3, 5, apply=True, versions=preview["versions"])
    assert result["applied"]
    second.refresh_from_db()
    third.refresh_from_db()
    first.refresh_from_db()
    execution.refresh_from_db()
    assert second.due_on == timezone.localdate() + timedelta(days=8)
    assert third.due_on == timezone.localdate() + timedelta(days=9)
    assert first.created_at == created and execution.end_at == execution_due
    assert calendar_dates(first)["start"] == timezone.localdate()


def test_stale_descendant_aborts_entire_cascade(context):
    owner, _ = context
    first = dated(context, "Préparer", 1, 2)
    second = dated(context, "Livrer", 3, 4)
    depend(owner, second, first)
    preview = plan(owner, first, 3, 4)
    change(owner, second, blocked_reason="Fournisseur indisponible")
    with pytest.raises(SignalStateError):
        plan(owner, first, 3, 4, apply=True, versions=preview["versions"])
    first.refresh_from_db()
    assert first.due_on == timezone.localdate() + timedelta(days=2)


def test_planning_requires_preview_versions_and_manager(context):
    owner, source = context
    record = dated(context, "Préparer", 1, 2)
    with pytest.raises(SignalStateError):
        plan(owner, record, 3, 4, apply=True)
    staff = build_api_membership_on_establishment(owner, role="staff")
    assign_business_unit_scope(staff, source.responsible_business_unit)
    change(owner, record, owner_membership_id=staff.id)
    with pytest.raises(SignalPermissionError):
        plan(staff, record, 3, 4)


def test_closed_descendant_refuses_shift_and_atomic_changes(context):
    owner, _ = context
    first = dated(context, "Préparer", 1, 2)
    second = dated(context, "Livrer", 3, 4)
    depend(owner, second, first)
    change(owner, second, stage="closed", closure_reason="acknowledged")
    with pytest.raises(SignalStateError):
        plan(owner, first, 3, 4)
    first.refresh_from_db()
    assert first.due_on == timezone.localdate() + timedelta(days=2)


def test_earlier_finish_does_not_pull_successors_and_date_edit_cannot_bypass(context):
    owner, _ = context
    first = dated(context, "Préparer", 1, 3)
    second = dated(context, "Livrer", 4, 5)
    depend(owner, second, first)
    assert len(plan(owner, first, 1, 2)["changes"]) == 1
    with pytest.raises(SignalValidationError):
        change(owner, first, due_on=timezone.localdate() + timedelta(days=9))
    with pytest.raises(SignalValidationError):
        change(owner, second, planned_start_on=timezone.localdate())
    with pytest.raises(SignalValidationError):
        depend(owner, first, second)


def test_milestones_require_date_and_single_day(context):
    owner, _ = context
    with pytest.raises(SignalValidationError):
        make(context, is_milestone=True)
    record = make(context, is_milestone=True, due_on=timezone.localdate() + timedelta(days=7))
    with pytest.raises(SignalValidationError):
        plan(owner, record, 3, 4)
    with pytest.raises(SignalValidationError):
        change(owner, record, due_on=None)
    assert plan(owner, record, 8, 8)["changes"]


def attach(owner, execution, filename="implantation.pdf"):
    comment = Comment.objects.create(
        establishment=owner.establishment,
        action_plan_execution=execution,
        author_membership=owner,
        body="Version pour le chantier",
    )
    upload = ActionPlanCommentUpload.objects.create(
        establishment=owner.establishment,
        action_plan_execution=execution,
        uploaded_by_membership=owner,
        original_filename=filename,
        declared_content_type="application/pdf",
        declared_size_bytes=42,
        content_type="application/pdf",
        size_bytes=42,
        kind="document",
        storage_key=f"test/{uuid4()}.pdf",
        status="linked",
        expires_at=timezone.now(),
    )
    return ActionPlanCommentAttachment.objects.create(
        comment=comment,
        upload=upload,
        action_plan_execution=execution,
        position=0,
        kind="document",
        content_type="application/pdf",
        size_bytes=42,
        original_filename=filename,
    )


def test_documents_search_origin_and_retention(context):
    owner, record = context
    execution = work(owner, record)
    attachment = attach(owner, execution)
    result = record_documents(actor=owner, record=record, query="implant")
    assert len(result["items"]) == 1
    assert str(result["items"][0]["comment_id"]) == str(attachment.comment_id)
    assert result["items"][0]["execution_id"] == execution.id
    assert record_documents(actor=owner, record=record, query="absent")["items"] == []
    execution.status = "done"
    execution.validated_at = timezone.now() - timedelta(days=1000)
    execution.save(update_fields=["status", "validated_at"])
    assert record_documents(actor=owner, record=record)["items"] == []


def test_documents_never_broaden_execution_visibility(context):
    owner, record = context
    execution = work(owner, record)
    attach(owner, execution)
    staff = build_api_membership_on_establishment(owner, role="staff")
    # No scope/assignment to this execution: knowing the signal cannot expose its files.
    assert record_documents(actor=staff, record=record)["items"] == []
    foreign = build_api_membership(role="owner")
    assert record_documents(actor=foreign, record=record)["items"] == []


def test_api_preview_serialization_and_project_filter(api_client, context):
    owner, _ = context
    project = make(context, is_project=True)
    child = make(context, parent_project_id=project.id)
    token = login(api_client, user=owner.user)
    root = f"/api/v1/establishments/{owner.establishment_id}/records/"
    response = api_client.get(f"{root}?project={project.id}", **auth_headers(token))
    assert response.status_code == 200, response.content
    assert [r["id"] for r in response.json()["items"]] == [str(child.id)]
    child.refresh_from_db()
    payload = {
        "expected_updated_at": child.updated_at.isoformat(),
        "start_on": str(timezone.localdate()),
        "due_on": str(timezone.localdate() + timedelta(days=2)),
    }
    preview = api_client.post(
        f"{root}{child.id}/planning/", payload, format="json", **auth_headers(token)
    )
    assert preview.status_code == 200, preview.content
    payload.update(apply=True, expected_versions=preview.json()["versions"])
    response = api_client.post(
        f"{root}{child.id}/planning/", payload, format="json", **auth_headers(token)
    )
    assert response.status_code == 200, response.content
    assert response.json()["applied"]
    assert record_queryset(owner).filter(is_project=True).count() == 1
