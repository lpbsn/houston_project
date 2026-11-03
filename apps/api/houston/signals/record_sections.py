"""Bounded detail reads, with execution and Brain access checked independently."""

from django.db.models import F, Prefetch, Q

from houston.accounts.display import membership_display_name
from houston.action_plans.selectors import action_plan_execution_feed_queryset
from houston.observations.models import Observation
from houston.signals.models import CandidateSignal
from houston.signals.record_selectors import linked_executions

LABELS = {
    "created": "Fiche créée",
    "updated": "Fiche mise à jour",
    "assigned": "Responsable modifié",
    "closed": "Fiche close",
    "reopened": "Fiche rouverte",
    "review_requested": "Résultat à vérifier",
    "taken_in_charge": "Fiche prise en charge",
    "linked": "Travail rattaché",
    "participants_changed": "Participants mis à jour",
    "work_added": "Travail ajouté",
    "dependency_changed": "Dépendance mise à jour",
    "objective_linked": "Objectif KPI rattaché",
}


def record_section(*, record, actor, section, offset):
    if section == "work":
        allowed = action_plan_execution_feed_queryset(membership=actor, view_mode="general")
        rows = (
            linked_executions(record)
            .filter(pk__in=allowed.values("pk"))
            .order_by("created_at", "id")
        )

        def render(row):
            return {
                "id": row.id,
                "title": row.title,
                "text": row.description,
                "author": "",
                "date": row.created_at,
                "status": row.status,
            }
    elif section == "sources":
        rows = (
            Observation.objects.filter(
                establishment_id=record.establishment_id,
                linked_signals__signal=record,
            )
            .select_related("submitted_by_membership__user")
            .prefetch_related(
                Prefetch(
                    "candidate_signals",
                    queryset=CandidateSignal.objects.filter(result_signal=record),
                    to_attr="record_candidates",
                )
            )
            .distinct()
            .order_by("-submitted_at", "-id")
        )

        def render(row):
            candidates = row.record_candidates
            text = "\n".join(c.structured_summary for c in candidates if c.structured_summary)
            # Raw observations retain their owner-only permission, including pending intake.
            if actor.role == "owner":
                text = row.raw_text
            return {
                "id": row.id,
                "title": candidates[0].title if candidates else "Observation reçue",
                "text": text or "Contenu en préparation. Le témoignage original est conservé.",
                "author": membership_display_name(row.submitted_by_membership) or "",
                "date": row.submitted_at,
                "status": "",
            }
    elif section == "history":
        return history_page(record, offset)
    else:
        from houston.brain.models import BrainObjective

        rows = (
            BrainObjective.objects.filter(
                record_links__signal=record,
                establishment_id=record.establishment_id,
                current_revision__isnull=False,
            )
            .select_related("current_revision")
            .order_by("-created_at", "-id")
        )
        if actor.role not in ("owner", "director"):
            rows = rows.none()

        def render(row):
            revision = row.current_revision
            return {
                "id": row.id,
                "title": revision.indicator,
                "text": (
                    f"{revision.reference} → {revision.target} · "
                    f"Bilan : {revision.due_on or 'à définir'}"
                ),
                "author": "",
                "date": row.created_at,
                "status": revision.decision,
            }

    page = list(rows[offset : offset + 21])
    return {
        "items": [render(row) for row in page[:20]],
        "next_offset": offset + 20 if len(page) > 20 else None,
    }


def history_page(record, offset):
    from houston.establishments.models import EstablishmentMembership
    from houston.signals.models import Signal, SignalAlias, SignalLifecycleEvent, SignalRecordEvent

    ids = (
        Signal.objects.filter(establishment_id=record.establishment_id)
        .filter(
            Q(pk=record.id)
            | Q(pk__in=SignalAlias.objects.filter(target=record).values("former_signal_id"))
        )
        .values("id")
    )
    fields = ("id", "kind", "date", "person_id", "changes")
    modern = (
        SignalRecordEvent.objects.filter(signal_id__in=ids)
        .annotate(date=F("created_at"), person_id=F("actor_id"))
        .values(*fields)
    )
    old = (
        SignalLifecycleEvent.objects.filter(signal_id__in=ids)
        .filter(Q(metadata_safe__origin__isnull=True) | ~Q(metadata_safe__origin="record"))
        .annotate(
            kind=F("event_type"),
            date=F("occurred_at"),
            person_id=F("actor_membership_id"),
            changes=F("metadata_safe"),
        )
        .values(*fields)
    )
    page = list(modern.union(old).order_by("-date", "-id")[offset : offset + 21])
    people = {
        m.id: membership_display_name(m)
        for m in EstablishmentMembership.objects.filter(
            establishment_id=record.establishment_id, id__in=[r["person_id"] for r in page]
        ).select_related("user")
    }
    labels = {
        **LABELS,
        "signal.created": "Observation reçue",
        "signal.resolved": "Résolution confirmée",
        "signal.canceled": "Sujet clos",
        "signal.moved_open": "Sujet à traiter",
        "signal.moved_in_progress": "Sujet en cours",
        "signal.marked_interesting": "Sujet retenu",
        "signal.history_baseline": "État historique",
    }
    items = []
    for row in page[:20]:
        changes = row["changes"] or {}
        notes = []
        for key, label in (
            ("due_on", "Échéance"),
            ("blocked_reason", "Blocage"),
            ("title", "Titre"),
        ):
            value = changes.get(key)
            if isinstance(value, dict):
                notes.append(f"{label} : {value.get('after') or 'retiré'}")
        reason = changes.get("closure_reason")
        if reason:
            notes.append(
                {
                    "resolved": "Problème résolu",
                    "acknowledged": "Information prise en compte",
                    "abandoned": "Abandonné",
                }.get(reason, "")
            )
        items.append(
            {
                "id": row["id"],
                "title": labels.get(row["kind"], "Suivi mis à jour"),
                "text": " · ".join(notes),
                "author": people.get(row["person_id"], "Spore"),
                "date": row["date"],
                "status": "",
            }
        )
    return {"items": items, "next_offset": offset + 20 if len(page) > 20 else None}
