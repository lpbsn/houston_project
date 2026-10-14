"""Editable plan suggestions. Confirmation calls the Houston plan service once."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from houston.action_plans.exceptions import ActionPlanPermissionError, ActionPlanValidationError
from houston.action_plans.services import create_action_plan_with_execution
from houston.brain.errors import BrainAccessDenied, BrainWorkError
from houston.brain.models import BrainSuggestion, BrainSuggestionRevision
from houston.brain.selectors import plans_opened_since_capture
from houston.establishments.permissions import resolve_establishment_admin_actor


@dataclass(frozen=True)
class SuggestionConversion:
    action_plan_id: uuid.UUID
    created: bool
    related_plan_ids: tuple[uuid.UUID, ...]


def publish_suggested_drafts(analysis, proposals) -> None:
    """Insert drafts for this completion. Does not create a Houston plan."""
    if not isinstance(proposals, list):
        return
    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        key = str(proposal.get("key") or "").strip()
        title = str(proposal.get("title") or "").strip()
        if not key or not title:
            continue
        if BrainSuggestion.objects.filter(analysis_id=analysis.id, stable_key=key).exists():
            continue
        suggestion = BrainSuggestion.objects.create(
            establishment_id=analysis.establishment_id,
            analysis=analysis,
            stable_key=key,
        )
        revision = BrainSuggestionRevision.objects.create(
            suggestion=suggestion,
            number=1,
            title=title[:200],
            description=str(proposal.get("description") or "")[:2000],
            tasks=_tasks(proposal.get("tasks")),
            pilot_business_unit_id=_uuid(proposal.get("pilot_business_unit_id")),
            assignees=_assignees(proposal.get("assignees")),
            edited_by_id=analysis.author_id,
        )
        suggestion.current_revision = revision
        suggestion.save(update_fields=["current_revision", "updated_at"])


def revise_suggestion(
    *,
    user,
    suggestion_id,
    expected_revision_id,
    title: str,
    description: str = "",
    tasks: list | None = None,
    pilot_business_unit_id=None,
    assignees: list | None = None,
    start_at=None,
    end_at=None,
    occurrence_date=None,
    all_day: bool = False,
    requires_validation: bool = True,
) -> BrainSuggestionRevision:
    """Append a revision. A stale expected revision does not replace the newer one."""
    with transaction.atomic():
        suggestion = _locked(suggestion_id)
        _require_admin(user, suggestion.establishment_id)
        if suggestion.status == BrainSuggestion.Status.CONVERTED:
            raise BrainWorkError(
                code="suggestion_already_converted",
                message="Cette suggestion est déjà convertie.",
            )
        current = suggestion.current_revision
        if current is None or current.id != expected_revision_id:
            raise BrainWorkError(
                code="suggestion_revision_conflict",
                message="Une révision plus récente existe déjà sur cette suggestion.",
            )
        revision = BrainSuggestionRevision.objects.create(
            suggestion=suggestion,
            number=current.number + 1,
            title=title.strip()[:200],
            description=description[:2000],
            tasks=_tasks(tasks),
            pilot_business_unit_id=_uuid(pilot_business_unit_id),
            assignees=_assignees(assignees),
            start_at=start_at,
            end_at=end_at,
            occurrence_date=occurrence_date,
            all_day=all_day,
            requires_validation=requires_validation,
            edited_by=user,
        )
        suggestion.current_revision = revision
        suggestion.save(update_fields=["current_revision", "updated_at"])
        return revision


def convert_suggestion(*, user, suggestion_id, expected_revision_id) -> SuggestionConversion:
    """Confirm one draft. A converted suggestion is not created again, even if its plan is gone."""
    with transaction.atomic():
        suggestion = _locked(suggestion_id)
        actor = resolve_establishment_admin_actor(user, suggestion.establishment_id)
        if actor is None:
            raise BrainAccessDenied()
        if suggestion.action_plan_id is not None:
            return SuggestionConversion(
                action_plan_id=suggestion.action_plan_id,
                created=False,
                related_plan_ids=(),
            )
        current = suggestion.current_revision
        if current is None or current.id != expected_revision_id:
            raise BrainWorkError(
                code="suggestion_revision_conflict",
                message="Une révision plus récente existe déjà sur cette suggestion.",
            )
        if not current.assignees:
            raise BrainWorkError(
                code="assignee_required",
                message="La suggestion n'a pas de responsable désigné.",
            )
        if current.pilot_business_unit_id is None:
            raise BrainWorkError(
                code="suggestion_pole_required",
                message="La suggestion n'a pas de pôle.",
            )
        try:
            plan, _execution = create_action_plan_with_execution(
                establishment_id=suggestion.establishment_id,
                created_by=actor.membership,
                pilot_business_unit_id=current.pilot_business_unit_id,
                title=current.title,
                description=current.description,
                requires_validation=current.requires_validation,
                tasks=list(current.tasks or []),
                assignees=list(current.assignees or []),
                use_shared_chronology=len(current.assignees or []) != 1,
                start_at=current.start_at,
                end_at=current.end_at,
                occurrence_date=current.occurrence_date,
                all_day=current.all_day,
            )
        except ActionPlanPermissionError as exc:
            raise BrainWorkError(
                code="action_plan_permission",
                message="Le droit courant ne permet pas de créer ce Plan.",
            ) from exc
        except ActionPlanValidationError as exc:
            raise BrainWorkError(
                code="action_plan_invalid",
                message="Le Plan proposé n'est pas valide.",
            ) from exc
        suggestion.status = BrainSuggestion.Status.CONVERTED
        suggestion.action_plan_id = plan.id
        suggestion.converted_at = timezone.now()
        suggestion.converted_by = user
        suggestion.save(
            update_fields=[
                "status",
                "action_plan_id",
                "converted_at",
                "converted_by",
                "updated_at",
            ]
        )
        related = plans_opened_since_capture(
            establishment_id=suggestion.establishment_id,
            analysis_id=suggestion.analysis_id,
            pilot_business_unit_id=current.pilot_business_unit_id,
            exclude_plan_id=plan.id,
        )
        return SuggestionConversion(
            action_plan_id=plan.id,
            created=True,
            related_plan_ids=tuple(related),
        )


def _locked(suggestion_id) -> BrainSuggestion:
    suggestion = (
        BrainSuggestion.objects.select_for_update(of=("self",))
        .select_related("current_revision")
        .filter(pk=suggestion_id)
        .first()
    )
    if suggestion is None:
        raise BrainWorkError(
            code="suggestion_not_found",
            message="La suggestion est introuvable.",
        )
    return suggestion


def _require_admin(user, establishment_id) -> None:
    if resolve_establishment_admin_actor(user, establishment_id) is None:
        raise BrainAccessDenied()


def _tasks(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    tasks = []
    for index, item in enumerate(value[:10], start=1):
        if not isinstance(item, dict):
            continue
        text = str(item.get("task") or "").strip()
        if not text:
            continue
        position = item.get("position", index)
        if not isinstance(position, int):
            position = index
        tasks.append(
            {
                "task": text[:500],
                "description": str(item.get("description") or "")[:2000],
                "business_unit_id": _text_uuid(item.get("business_unit_id")),
                "position": position,
            }
        )
    return tasks


def _assignees(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    assignees = []
    seen = set()
    for item in value[:20]:
        if not isinstance(item, dict):
            continue
        membership_id = _text_uuid(item.get("membership_id"))
        business_unit_id = _text_uuid(item.get("business_unit_id"))
        if membership_id is None or business_unit_id is None or membership_id in seen:
            continue
        seen.add(membership_id)
        assignees.append(
            {
                "membership_id": membership_id,
                "business_unit_id": business_unit_id,
            }
        )
    return assignees


def _uuid(value):
    text = _text_uuid(value)
    if text is None:
        return None
    return uuid.UUID(text)


def _text_uuid(value) -> str | None:
    if value is None or value == "":
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None
