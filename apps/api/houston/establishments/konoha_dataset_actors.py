from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from django.test import RequestFactory

from houston.accounts.models import User
from houston.core.dev_guards import assert_local_dev_environment
from houston.establishments.membership_scope import MembershipScopeInput, MembershipScopeType
from houston.establishments.models import (
    BusinessUnit,
    Establishment,
    EstablishmentMembership,
    MembershipScope,
)
from houston.establishments.services import (
    accept_establishment_invitation,
    invite_membership_for_establishment,
    reinvite_membership_for_establishment,
)
from houston.organizations.models import Organization

ORGANIZATION_NAME = "KONOHA"
ESTABLISHMENT_ANBU = "ANBU"
ESTABLISHMENT_AKATSUKI = "AKATSUKI"
NARUTO_USERNAME = "naruto"
NARUTO_EMAIL = "naruto@konoha.com"
LOCAL_DATASET_PASSWORD = "SecurePass123!"
EXPECTED_MANAGERS_PER_POLE = 2
EXPECTED_STAFF_PER_POLE = 3

POLE_HOTEL = "Hôtel"
POLE_ISHIRAKU = "Ishiraku Ramen"
POLE_YAKINUKU = "Yakinuku Grill"
POLE_COWORKING = "Coworking"
POLE_MAINTENANCE = "Maintenance"
POLE_COMMUNICATION = "Communication"
POLE_COMMERCE = "Commerce"
POLE_BASIC_FIT = "Basic Fit"
POLE_EMEA = "EMEA"
POLE_EVENEMENTS = "Événements & privatisations"


class SeatAction(str, Enum):
    SKIP = "skip"
    INVITE_ACCEPT = "invite_accept"
    REINVITE_ACCEPT = "reinvite_accept"
    ERROR = "error"


@dataclass(frozen=True)
class DatasetSeat:
    email: str
    first_name: str
    last_name: str
    role: str
    establishment_name: str
    pole_specific_name: str


@dataclass(frozen=True)
class SeatClassification:
    seat: DatasetSeat
    action: SeatAction
    reason: str
    membership_id: UUID | None = None


@dataclass(frozen=True)
class PreflightResult:
    classifications: tuple[SeatClassification, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class ProvisionResult:
    dry_run: bool
    skipped: int
    invited_accepted: int
    reinvited_accepted: int
    errors: tuple[str, ...]


class KonohaDatasetActorsError(Exception):
    def __init__(self, messages: tuple[str, ...] | list[str]):
        self.messages = tuple(messages)
        super().__init__("; ".join(self.messages))


def _seat(
    email: str,
    first_name: str,
    last_name: str,
    role: str,
    establishment_name: str,
    pole_specific_name: str,
) -> DatasetSeat:
    return DatasetSeat(
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
        establishment_name=establishment_name,
        pole_specific_name=pole_specific_name,
    )


KONOHA_DATASET_SEATS: tuple[DatasetSeat, ...] = (
    _seat(
        "anbu.hotel.mgr1@konoha.test",
        "Asuma",
        "Sarutobi",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_ANBU,
        POLE_HOTEL,
    ),
    _seat(
        "anbu.hotel.mgr2@konoha.test",
        "Kurenai",
        "Yuhi",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_ANBU,
        POLE_HOTEL,
    ),
    _seat(
        "anbu.hotel.staff1@konoha.test",
        "Iruka",
        "Umino",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_HOTEL,
    ),
    _seat(
        "anbu.hotel.staff2@konoha.test",
        "Anko",
        "Mitarashi",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_HOTEL,
    ),
    _seat(
        "anbu.hotel.staff3@konoha.test",
        "Genma",
        "Shiranui",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_HOTEL,
    ),
    _seat(
        "anbu.ishiraku.mgr2@konoha.test",
        "Ayame",
        "Ishiraku",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_ANBU,
        POLE_ISHIRAKU,
    ),
    _seat(
        "anbu.ishiraku.staff2@konoha.test",
        "Konohamaru",
        "Sarutobi",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_ISHIRAKU,
    ),
    _seat(
        "anbu.ishiraku.staff3@konoha.test",
        "Moegi",
        "Kazamatsuri",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_ISHIRAKU,
    ),
    _seat(
        "anbu.yakinuku.mgr2@konoha.test",
        "Aoba",
        "Yamashiro",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_ANBU,
        POLE_YAKINUKU,
    ),
    _seat(
        "anbu.yakinuku.staff2@konoha.test",
        "Kotetsu",
        "Hagane",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_YAKINUKU,
    ),
    _seat(
        "anbu.yakinuku.staff3@konoha.test",
        "Izumo",
        "Kamizuki",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_YAKINUKU,
    ),
    _seat(
        "anbu.coworking.mgr1@konoha.test",
        "Shikamaru",
        "Nara",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_ANBU,
        POLE_COWORKING,
    ),
    _seat(
        "anbu.coworking.mgr2@konoha.test",
        "Ino",
        "Yamanaka",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_ANBU,
        POLE_COWORKING,
    ),
    _seat(
        "anbu.coworking.staff1@konoha.test",
        "Sai",
        "Yamanaka",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_COWORKING,
    ),
    _seat(
        "anbu.coworking.staff2@konoha.test",
        "Yamato",
        "Tenzo",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_COWORKING,
    ),
    _seat(
        "anbu.coworking.staff3@konoha.test",
        "Tenten",
        "Iwamizawa",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_COWORKING,
    ),
    _seat(
        "anbu.maintenance.mgr1@konoha.test",
        "Raidou",
        "Namiashi",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_ANBU,
        POLE_MAINTENANCE,
    ),
    _seat(
        "anbu.maintenance.mgr2@konoha.test",
        "Iwashi",
        "Tatami",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_ANBU,
        POLE_MAINTENANCE,
    ),
    _seat(
        "anbu.maintenance.staff1@konoha.test",
        "Kiba",
        "Inuzuka",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_MAINTENANCE,
    ),
    _seat(
        "anbu.maintenance.staff2@konoha.test",
        "Shino",
        "Aburame",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_MAINTENANCE,
    ),
    _seat(
        "anbu.maintenance.staff3@konoha.test",
        "Rock",
        "Lee",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_MAINTENANCE,
    ),
    _seat(
        "anbu.communication.mgr2@konoha.test",
        "Shizune",
        "Kato",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_ANBU,
        POLE_COMMUNICATION,
    ),
    _seat(
        "anbu.communication.staff1@konoha.test",
        "Inoichi",
        "Yamanaka",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_COMMUNICATION,
    ),
    _seat(
        "anbu.communication.staff2@konoha.test",
        "Ibiki",
        "Morino",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_COMMUNICATION,
    ),
    _seat(
        "anbu.communication.staff3@konoha.test",
        "Mozuku",
        "Tanzaku",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_ANBU,
        POLE_COMMUNICATION,
    ),
    _seat(
        "akatsuki.commerce.mgr1@konoha.test",
        "Kakuzu",
        "Takigakure",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_AKATSUKI,
        POLE_COMMERCE,
    ),
    _seat(
        "akatsuki.commerce.mgr2@konoha.test",
        "Sasori",
        "Akasuna",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_AKATSUKI,
        POLE_COMMERCE,
    ),
    _seat(
        "akatsuki.commerce.staff1@konoha.test",
        "Deidara",
        "Tsuchigakure",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_COMMERCE,
    ),
    _seat(
        "akatsuki.commerce.staff2@konoha.test",
        "Hidan",
        "Yugakure",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_COMMERCE,
    ),
    _seat(
        "akatsuki.commerce.staff3@konoha.test",
        "Zetsu",
        "Gedou",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_COMMERCE,
    ),
    _seat(
        "akatsuki.basic-fit.mgr1@konoha.test",
        "Kisame",
        "Hoshigaki",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_AKATSUKI,
        POLE_BASIC_FIT,
    ),
    _seat(
        "akatsuki.basic-fit.mgr2@konoha.test",
        "Konan",
        "Ame",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_AKATSUKI,
        POLE_BASIC_FIT,
    ),
    _seat(
        "akatsuki.basic-fit.staff1@konoha.test",
        "Itachi",
        "Uchiha",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_BASIC_FIT,
    ),
    _seat(
        "akatsuki.basic-fit.staff2@konoha.test",
        "Obito",
        "Uchiha",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_BASIC_FIT,
    ),
    _seat(
        "akatsuki.basic-fit.staff3@konoha.test",
        "Juugo",
        "Tsuchigumo",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_BASIC_FIT,
    ),
    _seat(
        "akatsuki.emea.mgr1@konoha.test",
        "Yahiko",
        "Ame",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_AKATSUKI,
        POLE_EMEA,
    ),
    _seat(
        "akatsuki.emea.mgr2@konoha.test",
        "Orochimaru",
        "Oto",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_AKATSUKI,
        POLE_EMEA,
    ),
    _seat(
        "akatsuki.emea.staff1@konoha.test",
        "Kabuto",
        "Yakushi",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_EMEA,
    ),
    _seat(
        "akatsuki.emea.staff2@konoha.test",
        "Karin",
        "Uzumaki",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_EMEA,
    ),
    _seat(
        "akatsuki.emea.staff3@konoha.test",
        "Suigetsu",
        "Hozuki",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_EMEA,
    ),
    _seat(
        "akatsuki.evenements.mgr1@konoha.test",
        "Temari",
        "Sabaku",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_AKATSUKI,
        POLE_EVENEMENTS,
    ),
    _seat(
        "akatsuki.evenements.mgr2@konoha.test",
        "Kankuro",
        "Sabaku",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_AKATSUKI,
        POLE_EVENEMENTS,
    ),
    _seat(
        "akatsuki.evenements.staff1@konoha.test",
        "Gaara",
        "Sabaku",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_EVENEMENTS,
    ),
    _seat(
        "akatsuki.evenements.staff2@konoha.test",
        "Matsuri",
        "Sabaku",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_EVENEMENTS,
    ),
    _seat(
        "akatsuki.evenements.staff3@konoha.test",
        "Yukata",
        "Suna",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_EVENEMENTS,
    ),
    _seat(
        "akatsuki.maintenance.mgr1@konoha.test",
        "Killer",
        "Bee",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_AKATSUKI,
        POLE_MAINTENANCE,
    ),
    _seat(
        "akatsuki.maintenance.mgr2@konoha.test",
        "Darui",
        "Kumo",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_AKATSUKI,
        POLE_MAINTENANCE,
    ),
    _seat(
        "akatsuki.maintenance.staff1@konoha.test",
        "Cee",
        "Kumo",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_MAINTENANCE,
    ),
    _seat(
        "akatsuki.maintenance.staff2@konoha.test",
        "Omoi",
        "Kumo",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_MAINTENANCE,
    ),
    _seat(
        "akatsuki.maintenance.staff3@konoha.test",
        "Karui",
        "Kumo",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_MAINTENANCE,
    ),
    _seat(
        "akatsuki.communication.mgr1@konoha.test",
        "Shikaku",
        "Nara",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_AKATSUKI,
        POLE_COMMUNICATION,
    ),
    _seat(
        "akatsuki.communication.mgr2@konoha.test",
        "Mabui",
        "Kumo",
        EstablishmentMembership.Role.MANAGER,
        ESTABLISHMENT_AKATSUKI,
        POLE_COMMUNICATION,
    ),
    _seat(
        "akatsuki.communication.staff1@konoha.test",
        "Samui",
        "Kumo",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_COMMUNICATION,
    ),
    _seat(
        "akatsuki.communication.staff2@konoha.test",
        "Atsui",
        "Kumo",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_COMMUNICATION,
    ),
    _seat(
        "akatsuki.communication.staff3@konoha.test",
        "A",
        "Raikage",
        EstablishmentMembership.Role.STAFF,
        ESTABLISHMENT_AKATSUKI,
        POLE_COMMUNICATION,
    ),
)


@dataclass(frozen=True)
class _ResolvedContext:
    establishments: dict[str, Establishment]
    poles: dict[tuple[str, str], BusinessUnit]
    naruto_memberships: dict[str, EstablishmentMembership]


def _required_poles() -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            {(seat.establishment_name, seat.pole_specific_name) for seat in KONOHA_DATASET_SEATS}
        )
    )


def _scope_business_unit_ids(membership: EstablishmentMembership) -> frozenset[UUID]:
    return frozenset(
        MembershipScope.objects.filter(membership=membership).values_list(
            "business_unit_id",
            flat=True,
        )
    )


def classify_seat(
    seat: DatasetSeat,
    *,
    establishment: Establishment,
    business_unit: BusinessUnit,
) -> SeatClassification:
    user = User.objects.filter(email__iexact=seat.email).first()
    if user is None:
        return SeatClassification(
            seat=seat,
            action=SeatAction.INVITE_ACCEPT,
            reason="absent",
        )

    membership = EstablishmentMembership.objects.filter(
        user=user,
        establishment=establishment,
    ).first()
    if membership is None:
        return SeatClassification(
            seat=seat,
            action=SeatAction.ERROR,
            reason="user exists without membership on this establishment",
        )

    scope_ids = _scope_business_unit_ids(membership)
    expected_scopes = frozenset({business_unit.id})
    matching_scope = scope_ids == expected_scopes
    matching_role = membership.role == seat.role

    if (
        user.status == User.Status.ACTIVE
        and membership.status == EstablishmentMembership.Status.ACTIVE
        and matching_role
        and matching_scope
    ):
        return SeatClassification(
            seat=seat,
            action=SeatAction.SKIP,
            reason="already active",
            membership_id=membership.id,
        )

    if (
        user.status == User.Status.PENDING
        and membership.status == EstablishmentMembership.Status.INVITED
        and matching_role
        and matching_scope
    ):
        return SeatClassification(
            seat=seat,
            action=SeatAction.REINVITE_ACCEPT,
            reason="pending invited",
            membership_id=membership.id,
        )

    return SeatClassification(
        seat=seat,
        action=SeatAction.ERROR,
        reason=(
            f"mismatch user_status={user.status} membership_status={membership.status} "
            f"role={membership.role} scopes={len(scope_ids)}"
        ),
        membership_id=membership.id,
    )


def _load_naruto() -> User:
    user = User.objects.filter(
        username=NARUTO_USERNAME,
        email__iexact=NARUTO_EMAIL,
    ).first()
    if user is None:
        raise KonohaDatasetActorsError(
            (f"Naruto not found as {NARUTO_USERNAME} / {NARUTO_EMAIL}.",)
        )
    return user


def _require_naruto_owner(*, user: User, establishment: Establishment) -> EstablishmentMembership:
    membership = EstablishmentMembership.objects.filter(
        user=user,
        establishment=establishment,
    ).first()
    if (
        membership is None
        or membership.role != EstablishmentMembership.Role.OWNER
        or membership.status != EstablishmentMembership.Status.ACTIVE
    ):
        raise KonohaDatasetActorsError(
            (f"Naruto must be an active owner of {establishment.name}.",)
        )
    if _scope_business_unit_ids(membership):
        raise KonohaDatasetActorsError(
            (f"Naruto owner membership on {establishment.name} must have no scopes.",)
        )
    return membership


def _resolve_context() -> _ResolvedContext:
    organization = Organization.objects.filter(name=ORGANIZATION_NAME).first()
    if organization is None:
        raise KonohaDatasetActorsError((f"Organization {ORGANIZATION_NAME} not found.",))

    establishments: dict[str, Establishment] = {}
    for name in (ESTABLISHMENT_ANBU, ESTABLISHMENT_AKATSUKI):
        establishment = Establishment.objects.filter(
            organization=organization,
            name=name,
            status=Establishment.Status.ACTIVE,
        ).first()
        if establishment is None:
            raise KonohaDatasetActorsError(
                (f"Active establishment {name} not found in {ORGANIZATION_NAME}.",)
            )
        establishments[name] = establishment

    naruto = _load_naruto()
    naruto_memberships = {
        name: _require_naruto_owner(user=naruto, establishment=establishment)
        for name, establishment in establishments.items()
    }

    poles: dict[tuple[str, str], BusinessUnit] = {}
    missing: list[str] = []
    for establishment_name, pole_name in _required_poles():
        establishment = establishments[establishment_name]
        business_unit = BusinessUnit.objects.filter(
            establishment=establishment,
            specific_name=pole_name,
            active=True,
        ).first()
        if business_unit is None:
            missing.append(f"{establishment_name}/{pole_name}")
            continue
        poles[(establishment_name, pole_name)] = business_unit
    if missing:
        raise KonohaDatasetActorsError((f"Missing active poles: {', '.join(missing)}.",))

    scoped_admins = (
        EstablishmentMembership.objects.filter(
            establishment__in=establishments.values(),
            role__in={
                EstablishmentMembership.Role.OWNER,
                EstablishmentMembership.Role.DIRECTOR,
            },
        )
        .filter(scope_links__isnull=False)
        .distinct()
    )
    if scoped_admins.exists():
        raise KonohaDatasetActorsError(
            ("Owner or director memberships must not have operational scopes.",)
        )

    return _ResolvedContext(
        establishments=establishments,
        poles=poles,
        naruto_memberships=naruto_memberships,
    )


def _unique_scope_role_counts(
    *,
    establishment: Establishment,
    business_unit: BusinessUnit,
) -> tuple[int, int, tuple[str, ...]]:
    managers = 0
    staff = 0
    extras: list[str] = []
    memberships = EstablishmentMembership.objects.filter(
        establishment=establishment,
        status=EstablishmentMembership.Status.ACTIVE,
        role__in={
            EstablishmentMembership.Role.MANAGER,
            EstablishmentMembership.Role.STAFF,
        },
    )
    for membership in memberships:
        scope_ids = _scope_business_unit_ids(membership)
        if business_unit.id not in scope_ids:
            continue
        if scope_ids != frozenset({business_unit.id}):
            extras.append(
                f"{membership.user.email} has extra scopes on "
                f"{establishment.name}/{business_unit.specific_name}"
            )
            continue
        if membership.role == EstablishmentMembership.Role.MANAGER:
            managers += 1
        else:
            staff += 1
    return managers, staff, tuple(extras)


def preflight_konoha_dataset_actors() -> PreflightResult:
    context = _resolve_context()
    classifications = [
        classify_seat(
            seat,
            establishment=context.establishments[seat.establishment_name],
            business_unit=context.poles[(seat.establishment_name, seat.pole_specific_name)],
        )
        for seat in KONOHA_DATASET_SEATS
    ]
    errors = [
        (
            f"{item.seat.email} @ {item.seat.establishment_name}/"
            f"{item.seat.pole_specific_name}: {item.reason}"
        )
        for item in classifications
        if item.action == SeatAction.ERROR
    ]

    additions: dict[tuple[str, str, str], int] = {}
    for item in classifications:
        if item.action in {SeatAction.INVITE_ACCEPT, SeatAction.REINVITE_ACCEPT}:
            key = (
                item.seat.establishment_name,
                item.seat.pole_specific_name,
                item.seat.role,
            )
            additions[key] = additions.get(key, 0) + 1

    for establishment_name, pole_name in _required_poles():
        establishment = context.establishments[establishment_name]
        business_unit = context.poles[(establishment_name, pole_name)]
        managers, staff, extras = _unique_scope_role_counts(
            establishment=establishment,
            business_unit=business_unit,
        )
        errors.extend(extras)
        projected_managers = managers + additions.get(
            (establishment_name, pole_name, EstablishmentMembership.Role.MANAGER),
            0,
        )
        projected_staff = staff + additions.get(
            (establishment_name, pole_name, EstablishmentMembership.Role.STAFF),
            0,
        )
        if (
            projected_managers != EXPECTED_MANAGERS_PER_POLE
            or projected_staff != EXPECTED_STAFF_PER_POLE
        ):
            errors.append(
                f"{establishment_name}/{pole_name} projects "
                f"{projected_managers} managers and {projected_staff} staff; "
                f"expected {EXPECTED_MANAGERS_PER_POLE} and {EXPECTED_STAFF_PER_POLE}."
            )

    return PreflightResult(
        classifications=tuple(classifications),
        errors=tuple(errors),
    )


def _accept_invitation(*, invitation_token: str) -> None:
    accept_establishment_invitation(
        request=RequestFactory().post("/"),
        raw_token=invitation_token,
        password=LOCAL_DATASET_PASSWORD,
    )


def _provision_classified_seat(
    classification: SeatClassification,
    *,
    context: _ResolvedContext,
) -> SeatAction:
    if classification.action == SeatAction.SKIP:
        return SeatAction.SKIP

    seat = classification.seat
    establishment = context.establishments[seat.establishment_name]
    business_unit = context.poles[(seat.establishment_name, seat.pole_specific_name)]
    actor = context.naruto_memberships[seat.establishment_name]
    scopes = [
        MembershipScopeInput(
            scope_type=MembershipScopeType.BUSINESS_UNIT,
            scope_id=business_unit.id,
        )
    ]

    if classification.action == SeatAction.INVITE_ACCEPT:
        invitation = invite_membership_for_establishment(
            current_membership=actor,
            establishment_id=establishment.id,
            email=seat.email,
            first_name=seat.first_name,
            last_name=seat.last_name,
            role=seat.role,
            scopes=scopes,
        )
        _accept_invitation(invitation_token=invitation.invitation_token)
        return SeatAction.INVITE_ACCEPT

    if classification.action == SeatAction.REINVITE_ACCEPT:
        if classification.membership_id is None:
            raise KonohaDatasetActorsError((f"{seat.email} is missing membership_id.",))
        invitation = reinvite_membership_for_establishment(
            current_membership=actor,
            establishment_id=establishment.id,
            membership_id=classification.membership_id,
        )
        _accept_invitation(invitation_token=invitation.invitation_token)
        return SeatAction.REINVITE_ACCEPT

    raise KonohaDatasetActorsError((f"{seat.email}: unexpected action {classification.action}.",))


def _assert_exact_pole_counts(context: _ResolvedContext) -> None:
    errors: list[str] = []
    for establishment_name, pole_name in _required_poles():
        managers, staff, extras = _unique_scope_role_counts(
            establishment=context.establishments[establishment_name],
            business_unit=context.poles[(establishment_name, pole_name)],
        )
        errors.extend(extras)
        if managers != EXPECTED_MANAGERS_PER_POLE or staff != EXPECTED_STAFF_PER_POLE:
            errors.append(
                f"{establishment_name}/{pole_name} has {managers} managers and "
                f"{staff} staff; expected {EXPECTED_MANAGERS_PER_POLE} and "
                f"{EXPECTED_STAFF_PER_POLE}."
            )
    if errors:
        raise KonohaDatasetActorsError(errors)


def provision_konoha_dataset_actors(*, dry_run: bool) -> ProvisionResult:
    assert_local_dev_environment()
    preflight = preflight_konoha_dataset_actors()
    if preflight.errors:
        raise KonohaDatasetActorsError(preflight.errors)

    skipped = sum(1 for item in preflight.classifications if item.action == SeatAction.SKIP)
    to_invite = sum(
        1 for item in preflight.classifications if item.action == SeatAction.INVITE_ACCEPT
    )
    to_reinvite = sum(
        1 for item in preflight.classifications if item.action == SeatAction.REINVITE_ACCEPT
    )
    if dry_run:
        return ProvisionResult(
            dry_run=True,
            skipped=skipped,
            invited_accepted=to_invite,
            reinvited_accepted=to_reinvite,
            errors=(),
        )

    context = _resolve_context()
    invited_accepted = 0
    reinvited_accepted = 0
    for classification in preflight.classifications:
        action = _provision_classified_seat(classification, context=context)
        if action == SeatAction.INVITE_ACCEPT:
            invited_accepted += 1
        elif action == SeatAction.REINVITE_ACCEPT:
            reinvited_accepted += 1

    _assert_exact_pole_counts(context)
    return ProvisionResult(
        dry_run=False,
        skipped=skipped,
        invited_accepted=invited_accepted,
        reinvited_accepted=reinvited_accepted,
        errors=(),
    )
