from __future__ import annotations

from unittest.mock import patch

import pytest
from houston.accounts.models import SessionRefreshToken, UserSession
from houston.accounts.services import _revoke_refresh_token_family_for_reuse, revoke_session
from houston.establishments.membership_scope import MembershipScopeInput, MembershipScopeType
from houston.establishments.models import EstablishmentMembership
from houston.establishments.services import (
    MembershipUpdateInput,
    deactivate_membership_for_management,
    update_membership_for_management,
)
from houston.realtime.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    login,
)
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db(transaction=True)


def test_revoke_session_emits_session_revoked(api_client):
    establishment = create_establishment()
    user = create_user(username="realtime_revoke")
    create_membership(user=user, establishment=establishment)
    login(api_client, user=user)
    session = UserSession.objects.filter(user=user).order_by("-created_at").first()
    assert session is not None

    with patch("houston.realtime.broadcast.notify_access_event") as mock_notify:
        revoke_session(session=session)

        mock_notify.assert_called_once()
        assert mock_notify.call_args.kwargs["reason"] == "session.revoked"
        assert mock_notify.call_args.kwargs["session_id"] == session.id


def test_refresh_reuse_emits_session_revoked_with_reliable_session(api_client):
    establishment = create_establishment()
    user = create_user(username="realtime_reuse")
    create_membership(user=user, establishment=establishment)
    login(api_client, user=user)
    session = UserSession.objects.filter(user=user).order_by("-created_at").first()
    refresh = SessionRefreshToken.objects.filter(session=session).first()
    assert session is not None
    assert refresh is not None

    with patch("houston.realtime.broadcast.notify_access_event") as mock_notify:
        _revoke_refresh_token_family_for_reuse(
            session_id=session.id,
            family_id=refresh.family_id,
        )

        mock_notify.assert_called_once()
        assert mock_notify.call_args.kwargs["reason"] == "session.revoked"
        assert mock_notify.call_args.kwargs["session_id"] == session.id


def test_deactivate_membership_emits_membership_deactivated():
    establishment = create_establishment()
    owner = create_user(username="owner_deactivate")
    target = create_user(username="target_deactivate")
    owner_membership = create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    target_membership = create_membership(
        user=target,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )

    with patch("houston.realtime.broadcast.notify_access_event") as mock_notify:
        deactivate_membership_for_management(
            current_membership=owner_membership,
            establishment_id=establishment.id,
            membership_id=target_membership.id,
        )

        mock_notify.assert_called_once()
        assert mock_notify.call_args.kwargs["reason"] == "membership.deactivated"
        assert mock_notify.call_args.kwargs["membership_id"] == target_membership.id


def test_membership_updated_emits_on_role_change():
    establishment = create_establishment()
    owner = create_user(username="owner_update")
    target = create_user(username="target_update")
    owner_membership = create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    target_membership = create_membership(
        user=target,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    business_unit = create_business_unit(
        establishment=establishment,
        key="housekeeping",
        label="Housekeeping",
    )
    create_membership_with_business_unit_scope(
        membership=target_membership,
        business_unit=business_unit,
    )

    with patch("houston.realtime.broadcast.notify_access_event") as mock_notify:
        update_membership_for_management(
            current_membership=owner_membership,
            establishment_id=establishment.id,
            membership_id=target_membership.id,
            update_input=MembershipUpdateInput(
                role=EstablishmentMembership.Role.MANAGER,
                scopes=None,
            ),
        )

        mock_notify.assert_called_once()
        assert mock_notify.call_args.kwargs["reason"] == "membership.updated"


def test_membership_updated_no_op_does_not_emit():
    establishment = create_establishment()
    owner = create_user(username="owner_noop")
    target = create_user(username="target_noop")
    owner_membership = create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    target_membership = create_membership(
        user=target,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    business_unit = create_business_unit(
        establishment=establishment,
        key="housekeeping",
        label="Housekeeping",
    )
    create_membership_with_business_unit_scope(
        membership=target_membership,
        business_unit=business_unit,
    )

    with patch("houston.realtime.broadcast.notify_access_event") as mock_notify:
        update_membership_for_management(
            current_membership=owner_membership,
            establishment_id=establishment.id,
            membership_id=target_membership.id,
            update_input=MembershipUpdateInput(
                role=EstablishmentMembership.Role.STAFF,
                scopes=[
                    MembershipScopeInput(
                        scope_type=MembershipScopeType.BUSINESS_UNIT,
                        scope_id=business_unit.id,
                    )
                ],
            ),
        )

        mock_notify.assert_not_called()
