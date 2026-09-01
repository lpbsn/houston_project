from __future__ import annotations

import uuid

from django.db import transaction
from django.utils import timezone

from houston.accounts.deletion_constants import (
    INVALID_ACCOUNT_DELETION_PASSWORD_DETAIL,
    ORGANIZATION_CLOSURE_REQUIRED_DETAIL,
    REMOVED_COMMENT_BODY,
    REMOVED_OBSERVATION_TEXT,
)
from houston.accounts.models import User, UserSession
from houston.comments.models import Comment
from houston.establishments.account_closure_services import (
    close_organization_for_account_deletion,
    establishments_left_without_director,
    organizations_requiring_closure,
)
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.observations.media_services import (
    delete_all_observation_media,
    schedule_storage_files_deletion,
)
from houston.observations.models import Observation
from houston.uploads.models import TemporaryUpload


class InvalidAccountDeletionPasswordError(Exception):
    def __init__(self, detail: str = INVALID_ACCOUNT_DELETION_PASSWORD_DETAIL):
        self.detail = detail
        super().__init__(detail)


class OrganizationClosureRequiredError(Exception):
    def __init__(self, detail: str = ORGANIZATION_CLOSURE_REQUIRED_DETAIL):
        self.detail = detail
        super().__init__(detail)


def build_account_deletion_preview(*, user: User) -> dict:
    organizations = organizations_requiring_closure(user=user)
    without_director = establishments_left_without_director(user=user)
    return {
        "requires_organization_closure": bool(organizations),
        "organizations": [
            {
                "id": organization.id,
                "name": organization.name,
                "establishment_names": list(
                    organization.establishments.filter(
                        status__in=[
                            Establishment.Status.DRAFT,
                            Establishment.Status.ACTIVE,
                        ],
                    )
                    .order_by("name")
                    .values_list("name", flat=True)
                ),
            }
            for organization in organizations
        ],
        "leaves_establishments_without_director": [
            {
                "id": establishment.id,
                "name": establishment.name,
            }
            for establishment in without_director
        ],
    }


@transaction.atomic
def delete_authenticated_account(
    *,
    user: User,
    password: str,
    close_organizations: bool,
) -> None:
    if not user.check_password(password):
        raise InvalidAccountDeletionPasswordError

    required_orgs = organizations_requiring_closure(user=user)
    if required_orgs and not close_organizations:
        raise OrganizationClosureRequiredError

    memberships = list(
        EstablishmentMembership.objects.select_for_update()
        .filter(user=user)
        .order_by("id")
    )
    membership_ids = [membership.id for membership in memberships]

    if required_orgs and close_organizations:
        for organization in required_orgs:
            close_organization_for_account_deletion(organization=organization)

    _deactivate_user_memberships(memberships=memberships)
    _scrub_submitted_content(membership_ids=membership_ids)
    _delete_unlinked_uploads(user=user)
    _revoke_push_devices(user=user)
    _anonymize_user(user=user)
    _destroy_sessions(user=user)


def _deactivate_user_memberships(*, memberships: list[EstablishmentMembership]) -> None:
    from houston.chat.services import handle_membership_chat_deactivation
    from houston.establishments.services import _revoke_pending_invitations
    from houston.realtime.broadcast import schedule_access_event

    for membership in memberships:
        membership.refresh_from_db()
        if membership.status == EstablishmentMembership.Status.DEACTIVATED:
            continue
        membership.status = EstablishmentMembership.Status.DEACTIVATED
        membership.save(update_fields=["status", "updated_at"])
        _revoke_pending_invitations(membership=membership)
        handle_membership_chat_deactivation(membership=membership)
        schedule_access_event(
            reason="membership.deactivated",
            establishment_id=membership.establishment_id,
            membership_id=membership.id,
        )


def _scrub_submitted_content(*, membership_ids: list[uuid.UUID]) -> None:
    if not membership_ids:
        return

    from houston.chat.account_deletion import delete_messages_authored_by_memberships
    from houston.notifications.account_deletion import scrub_notifications_for_deleted_memberships

    observations = list(
        Observation.objects.filter(submitted_by_membership_id__in=membership_ids).order_by("id")
    )
    for observation in observations:
        delete_all_observation_media(observation_id=observation.id)
        if observation.raw_text != REMOVED_OBSERVATION_TEXT:
            observation.raw_text = REMOVED_OBSERVATION_TEXT
            observation.save(update_fields=["raw_text", "updated_at"])

    Comment.objects.filter(author_membership_id__in=membership_ids).exclude(
        body=REMOVED_COMMENT_BODY,
    ).update(body=REMOVED_COMMENT_BODY, updated_at=timezone.now())

    delete_messages_authored_by_memberships(membership_ids=membership_ids)
    scrub_notifications_for_deleted_memberships(membership_ids=membership_ids)


def _delete_unlinked_uploads(*, user: User) -> None:
    uploads = list(
        TemporaryUpload.objects.filter(
            uploaded_by=user,
            status=TemporaryUpload.Status.VALIDATED,
        ).order_by("id")
    )
    storage_keys: list[str] = []
    for upload in uploads:
        if upload.file:
            storage_keys.append(upload.file.name)
        upload.status = TemporaryUpload.Status.DELETED
        upload.save(update_fields=["status", "updated_at"])
    schedule_storage_files_deletion(storage_keys=storage_keys)


def _revoke_push_devices(*, user: User) -> None:
    from houston.notifications.models import PushDevice

    now = timezone.now()
    PushDevice.objects.filter(user=user, revoked_at__isnull=True).update(
        revoked_at=now,
        updated_at=now,
    )
    PushDevice.objects.filter(user=user).delete()


def _anonymize_user(*, user: User) -> None:
    user.status = User.Status.ANONYMIZED
    user.is_active = False
    user.email = None
    user.first_name = ""
    user.last_name = ""
    user.username = f"anon_{uuid.uuid4().hex}"
    user.set_unusable_password()
    user.save(
        update_fields=[
            "status",
            "is_active",
            "email",
            "first_name",
            "last_name",
            "username",
            "password",
            "updated_at",
        ]
    )


def _destroy_sessions(*, user: User) -> None:
    from houston.accounts.services import revoke_session

    sessions = list(UserSession.objects.filter(user=user).order_by("id"))
    for session in sessions:
        revoke_session(session=session)
    UserSession.objects.filter(user=user).delete()
