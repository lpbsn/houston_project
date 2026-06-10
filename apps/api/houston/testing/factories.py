from __future__ import annotations

import uuid

from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization

TEST_PASSWORD = "SecurePass123!"


def build_membership(
    *,
    role=EstablishmentMembership.Role.STAFF,
    membership_status=EstablishmentMembership.Status.ACTIVE,
    user_status=User.Status.ACTIVE,
    organization_status=Organization.Status.ACTIVE,
    establishment_status=Establishment.Status.ACTIVE,
):
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:8]}",
        status=organization_status,
    )
    user = User.objects.create_user(
        username=f"user_{uuid.uuid4().hex[:8]}",
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        password=TEST_PASSWORD,
        status=user_status,
    )
    establishment = Establishment.objects.create(
        name=f"Establishment {uuid.uuid4().hex[:8]}",
        organization=organization,
        status=establishment_status,
        timezone="UTC",
    )
    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=membership_status,
    )
    return membership


def create_user(
    *, username: str, status: str = User.Status.ACTIVE, password: str = TEST_PASSWORD
) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=password,
        status=status,
    )


def create_establishment(
    *,
    name: str = "Demo Hotel",
    timezone: str | None = None,
    status: str = Establishment.Status.ACTIVE,
    chat_enabled: bool = True,
) -> Establishment:
    organization = Organization.objects.create(
        name=f"{name} Group {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    kwargs = {
        "name": name,
        "organization": organization,
        "status": status,
        "chat_enabled": chat_enabled,
    }
    if timezone is not None:
        kwargs["timezone"] = timezone
    return Establishment.objects.create(**kwargs)


def create_membership(
    *,
    establishment: Establishment,
    user: User | None = None,
    role: str = EstablishmentMembership.Role.MANAGER,
    status: str = EstablishmentMembership.Status.ACTIVE,
) -> EstablishmentMembership:
    if user is None:
        user = create_user(username=f"user_{uuid.uuid4().hex[:8]}")
    return EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=status,
    )
