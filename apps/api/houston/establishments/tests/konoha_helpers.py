from __future__ import annotations

from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.testing.factories import TEST_PASSWORD
from houston.testing.taxonomy import create_membership_with_business_unit_scope

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


def create_named_user(
    *,
    username: str,
    email: str,
    first_name: str,
    last_name: str,
    status: str = User.Status.ACTIVE,
) -> User:
    user = User.objects.create_user(
        username=username,
        email=email,
        password=TEST_PASSWORD,
        first_name=first_name,
        last_name=last_name,
        status=status,
    )
    if status == User.Status.ACTIVE:
        from houston.accounts.legal_services import grant_current_legal_defaults

        grant_current_legal_defaults(user=user)
    return user


def create_scoped_member(
    *,
    username: str,
    email: str,
    first_name: str,
    last_name: str,
    establishment: Establishment,
    role: str,
    business_unit,
) -> EstablishmentMembership:
    user = create_named_user(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    return membership
