from __future__ import annotations

import uuid
from datetime import datetime
from datetime import timezone as dt_timezone

from django.db.models import (
    BooleanField,
    Case,
    Count,
    DateTimeField,
    Exists,
    F,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from houston.accounts.models import User
from houston.chat.models import ChatConversation, ChatMessage, ChatParticipant
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
)
from houston.organizations.models import Organization

_CUTOFF_SENTINEL = datetime(1970, 1, 1, tzinfo=dt_timezone.utc)


def canonical_dm_membership_pair(
    first: EstablishmentMembership,
    second: EstablishmentMembership,
) -> tuple[EstablishmentMembership, EstablishmentMembership]:
    if first.id < second.id:
        return first, second
    return second, first


def get_eligible_chat_memberships_queryset(
    *,
    establishment_id: uuid.UUID,
    query: str | None = None,
    exclude_active_conversation_id: uuid.UUID | None = None,
) -> QuerySet[EstablishmentMembership]:
    queryset = (
        EstablishmentMembership.objects.filter(
            establishment_id=establishment_id,
            status=EstablishmentMembership.Status.ACTIVE,
            user__status=User.Status.ACTIVE,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .select_related("user", "establishment", "establishment__organization")
        .order_by("user__first_name", "user__last_name", "user__username", "id")
    )
    if exclude_active_conversation_id is not None:
        active_membership_ids = active_participant_queryset(
            conversation_id=exclude_active_conversation_id,
        ).values_list("membership_id", flat=True)
        queryset = queryset.exclude(id__in=active_membership_ids)

    if not query:
        return queryset

    normalized = query.strip()
    if not normalized:
        return queryset

    return queryset.filter(
        Q(user__first_name__icontains=normalized)
        | Q(user__last_name__icontains=normalized)
        | Q(user__username__icontains=normalized)
        | Q(user__email__icontains=normalized)
    )


def active_participant_queryset(
    *,
    conversation_id: uuid.UUID,
) -> QuerySet[ChatParticipant]:
    return ChatParticipant.objects.filter(
        conversation_id=conversation_id,
        left_at__isnull=True,
    ).select_related("membership", "membership__user")


def get_active_participant(
    *,
    conversation_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> ChatParticipant | None:
    return (
        active_participant_queryset(conversation_id=conversation_id)
        .filter(membership_id=membership_id)
        .first()
    )


def get_conversation_for_participant(
    *,
    establishment_id: uuid.UUID,
    conversation_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> ChatConversation | None:
    return (
        ChatConversation.objects.filter(
            id=conversation_id,
            establishment_id=establishment_id,
            deleted_at__isnull=True,
            participants__membership_id=membership_id,
            participants__left_at__isnull=True,
        )
        .select_related("establishment", "created_by_membership", "created_by_membership__user")
        .prefetch_related(
            "participants__membership__user",
        )
        .distinct()
        .first()
    )


def list_conversations_for_membership(
    *,
    establishment_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> QuerySet[ChatConversation]:
    visible_last_message_at = Subquery(
        ChatMessage.objects.filter(conversation_id=OuterRef("pk"))
        .filter(
            created_at__gt=Coalesce(
                OuterRef("viewer_history_cutoff_at"),
                Value(_CUTOFF_SENTINEL),
            )
        )
        .order_by("-created_at")
        .values("created_at")[:1],
        output_field=DateTimeField(),
    )
    return (
        ChatConversation.objects.filter(
            establishment_id=establishment_id,
            deleted_at__isnull=True,
            participants__membership_id=membership_id,
            participants__left_at__isnull=True,
            participants__list_hidden_at__isnull=True,
        )
        .annotate(
            viewer_pinned_at=F("participants__pinned_at"),
            viewer_history_cutoff_at=F("participants__history_cutoff_at"),
            viewer_participant_role=F("participants__role"),
            is_pinned=Case(
                When(participants__pinned_at__isnull=False, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
            visible_last_message_at=Coalesce(
                visible_last_message_at,
                F("created_at"),
            ),
        )
        .select_related("created_by_membership", "created_by_membership__user")
        .prefetch_related("participants__membership__user")
        .distinct()
        .order_by(
            "-is_pinned",
            F("visible_last_message_at").desc(nulls_last=True),
            "-created_at",
            "-id",
        )
    )


def get_latest_message(conversation_id: uuid.UUID) -> ChatMessage | None:
    return get_latest_messages_by_conversation_ids([conversation_id]).get(conversation_id)


def get_latest_visible_message(
    conversation_id: uuid.UUID,
    *,
    history_cutoff_at: datetime | None = None,
) -> ChatMessage | None:
    return get_latest_messages_by_conversation_ids(
        [conversation_id],
        history_cutoffs_by_conversation_id={conversation_id: history_cutoff_at},
    ).get(conversation_id)


def get_latest_messages_by_conversation_ids(
    conversation_ids: list[uuid.UUID],
    *,
    history_cutoffs_by_conversation_id: dict[uuid.UUID, datetime | None] | None = None,
) -> dict[uuid.UUID, ChatMessage]:
    if not conversation_ids:
        return {}

    cutoffs = history_cutoffs_by_conversation_id or {}
    if not cutoffs:
        latest_messages = (
            ChatMessage.objects.filter(conversation_id__in=conversation_ids)
            .select_related("author_membership", "author_membership__user")
            .order_by("conversation_id", "-created_at", "-id")
            .distinct("conversation_id")
        )
        return {message.conversation_id: message for message in latest_messages}

    visibility_q = Q()
    for conversation_id in conversation_ids:
        cutoff = cutoffs.get(conversation_id)
        if cutoff is None:
            visibility_q |= Q(conversation_id=conversation_id)
        else:
            visibility_q |= Q(conversation_id=conversation_id, created_at__gt=cutoff)

    latest_messages = (
        ChatMessage.objects.filter(visibility_q)
        .select_related("author_membership", "author_membership__user")
        .order_by("conversation_id", "-created_at", "-id")
        .distinct("conversation_id")
    )
    return {message.conversation_id: message for message in latest_messages}


def list_messages_for_conversation(
    *,
    conversation_id: uuid.UUID,
    limit: int,
    before_created_at=None,
    before_id: uuid.UUID | None = None,
    history_cutoff_at: datetime | None = None,
) -> list[ChatMessage]:
    queryset = ChatMessage.objects.filter(conversation_id=conversation_id).select_related(
        "author_membership",
        "author_membership__user",
    )
    if history_cutoff_at is not None:
        queryset = queryset.filter(created_at__gt=history_cutoff_at)
    if before_created_at is not None and before_id is not None:
        queryset = queryset.filter(
            Q(created_at__lt=before_created_at) | Q(created_at=before_created_at, id__lt=before_id)
        )
    return list(queryset.order_by("-created_at", "-id")[:limit])


def _viewer_participant_marks_message_unread(*, membership_id: uuid.UUID) -> Exists:
    return Exists(
        ChatParticipant.objects.filter(
            conversation_id=OuterRef("conversation_id"),
            membership_id=membership_id,
            left_at__isnull=True,
        ).filter(
            Q(last_seen_message_created_at__isnull=True)
            | Q(last_seen_message_id__isnull=True)
            | Q(last_seen_message_created_at__lt=OuterRef("created_at"))
            | Q(
                last_seen_message_created_at=OuterRef("created_at"),
                last_seen_message_id__lt=OuterRef("id"),
            )
        )
    )


def _message_visible_after_viewer_cutoff(*, membership_id: uuid.UUID) -> Exists:
    return Exists(
        ChatParticipant.objects.filter(
            conversation_id=OuterRef("conversation_id"),
            membership_id=membership_id,
            left_at__isnull=True,
        ).filter(
            Q(history_cutoff_at__isnull=True)
            | Q(history_cutoff_at__lt=OuterRef("created_at"))
        )
    )


def get_unread_message_counts_by_conversation_ids(
    *,
    membership_id: uuid.UUID,
    conversation_ids: list[uuid.UUID],
) -> dict[uuid.UUID, int]:
    if not conversation_ids:
        return {}

    counts = dict.fromkeys(conversation_ids, 0)
    rows = (
        ChatMessage.objects.filter(conversation_id__in=conversation_ids)
        .exclude(author_membership_id=membership_id)
        .filter(_message_visible_after_viewer_cutoff(membership_id=membership_id))
        .filter(_viewer_participant_marks_message_unread(membership_id=membership_id))
        .values("conversation_id")
        .annotate(unread_count=Count("id"))
    )
    for row in rows:
        counts[row["conversation_id"]] = row["unread_count"]
    return counts


def count_unread_messages_for_participant(*, participant: ChatParticipant) -> int:
    queryset = ChatMessage.objects.filter(
        conversation_id=participant.conversation_id
    ).exclude(author_membership_id=participant.membership_id)
    if participant.history_cutoff_at is not None:
        queryset = queryset.filter(created_at__gt=participant.history_cutoff_at)
    if participant.last_seen_message_id is None or participant.last_seen_message_created_at is None:
        return queryset.count()
    return queryset.filter(
        Q(created_at__gt=participant.last_seen_message_created_at)
        | Q(
            created_at=participant.last_seen_message_created_at,
            id__gt=participant.last_seen_message_id,
        )
    ).count()


def find_existing_dm_conversation(
    *,
    establishment_id: uuid.UUID,
    membership_a_id: uuid.UUID,
    membership_b_id: uuid.UUID,
) -> ChatConversation | None:
    first_id, second_id = sorted((membership_a_id, membership_b_id))
    return ChatConversation.objects.filter(
        establishment_id=establishment_id,
        type=ChatConversation.Type.DM,
        deleted_at__isnull=True,
        dm_membership_a_id=first_id,
        dm_membership_b_id=second_id,
    ).first()
