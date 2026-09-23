from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RosterPerson:
    seed_key: str
    email: str
    first_name: str
    last_name: str
    role: str
    primary_pole: str | None
    secondary_pole: str | None
    status: str
    persona: bool
    badge_eligible: bool
    deactivate_on: str | None = None


def _p(
    slug: str,
    email: str,
    first: str,
    last: str,
    role: str,
    pole: str | None,
    *,
    secondary: str | None = None,
    status: str = "active",
    persona: bool = False,
    badge: bool = False,
    deactivate_on: str | None = None,
) -> RosterPerson:
    return RosterPerson(
        seed_key=f"member:{slug}",
        email=email,
        first_name=first,
        last_name=last,
        role=role,
        primary_pole=pole,
        secondary_pole=secondary,
        status=status,
        persona=persona,
        badge_eligible=badge,
        deactivate_on=deactivate_on,
    )


ROSTER: tuple[RosterPerson, ...] = (
    _p("director-demo", "director.demo.mama.nice@example.com", "Camille", "Morel", "director", None, persona=True, badge=True),
    _p("mgr-hotel-1", "mgr.hotel.demo@example.com", "Julien", "Fabre", "manager", "hotel", persona=True, badge=True),
    _p("mgr-hotel-2", "mgr.hotel.2@example.com", "Aline", "Perrin", "manager", "hotel", badge=True),
    _p("mgr-hotel-3", "mgr.hotel.3@example.com", "Benoît", "Giraud", "manager", "hotel"),
    _p("staff-hotel-1", "staff.hotel.demo@example.com", "Léa", "Martin", "staff", "hotel", persona=True, badge=True),
    _p("staff-hotel-2", "staff.hotel.2@example.com", "Paul", "Noel", "staff", "hotel", badge=True),
    _p("staff-hotel-3", "staff.hotel.3@example.com", "Chloé", "Renaud", "staff", "hotel"),
    _p("staff-hotel-4", "staff.hotel.4@example.com", "Hugo", "Blanc", "staff", "hotel"),
    _p("staff-hotel-5", "staff.hotel.5@example.com", "Manon", "Leroy", "staff", "hotel"),
    _p("staff-hotel-6", "staff.hotel.6@example.com", "Louis", "Carre", "staff", "hotel"),
    _p("staff-hotel-7", "staff.hotel.7@example.com", "Eva", "Marchal", "staff", "hotel"),
    _p("staff-hotel-8", "staff.hotel.8@example.com", "Noah", "Picard", "staff", "hotel"),
    _p("staff-hotel-9", "staff.hotel.9@example.com", "Lina", "Gautier", "staff", "hotel"),
    _p("mgr-pdj-1", "mgr.pdj.demo@example.com", "Sophie", "Lambert", "manager", "petit_dejeuner", secondary="restaurant", persona=True, badge=True),
    _p("mgr-pdj-2", "mgr.pdj.2@example.com", "Antoine", "Muller", "manager", "petit_dejeuner"),
    _p("staff-pdj-1", "staff.pdj.1@example.com", "Jade", "Henry", "staff", "petit_dejeuner", badge=True),
    _p("staff-pdj-2", "staff.pdj.2@example.com", "Adam", "Royer", "staff", "petit_dejeuner"),
    _p("staff-pdj-3", "staff.pdj.3@example.com", "Inès", "Colin", "staff", "petit_dejeuner"),
    _p("staff-pdj-4", "staff.pdj.4@example.com", "Tom", "Barbier", "staff", "petit_dejeuner"),
    _p("staff-pdj-5", "staff.pdj.5@example.com", "Léna", "Guillaume", "staff", "petit_dejeuner"),
    _p("mgr-resto-1", "mgr.restaurant.demo@example.com", "Nicolas", "Roux", "manager", "restaurant", secondary="petit_dejeuner", persona=True, badge=True),
    _p("mgr-resto-2", "mgr.restaurant.2@example.com", "Claire", "Marchand", "manager", "restaurant", badge=True),
    _p("mgr-resto-3", "mgr.restaurant.3@example.com", "Maxime", "Leclerc", "manager", "restaurant"),
    _p("mgr-resto-4", "mgr.restaurant.4@example.com", "Elodie", "Bonnet", "manager", "restaurant"),
    _p("mgr-resto-5", "mgr.restaurant.5@example.com", "Quentin", "Faure", "manager", "restaurant"),
    _p("staff-resto-1", "staff.restaurant.demo@example.com", "Inès", "Bernard", "staff", "restaurant", persona=True, badge=True),
    _p("staff-resto-2", "staff.restaurant.2@example.com", "Enzo", "Garcia", "staff", "restaurant", badge=True),
    _p("staff-resto-3", "staff.restaurant.3@example.com", "Sarah", "Lopez", "staff", "restaurant"),
    _p("staff-resto-4", "staff.restaurant.4@example.com", "Yanis", "Moreau", "staff", "restaurant"),
    _p("staff-resto-5", "staff.restaurant.5@example.com", "Nora", "Simon", "staff", "restaurant"),
    _p("staff-resto-6", "staff.restaurant.6@example.com", "Aaron", "Michel", "staff", "restaurant"),
    _p("staff-resto-7", "staff.restaurant.7@example.com", "Lila", "Lefevre", "staff", "restaurant"),
    _p("staff-resto-8", "staff.restaurant.8@example.com", "Milo", "Andre", "staff", "restaurant"),
    _p("staff-resto-9", "staff.restaurant.9@example.com", "Zoé", "Mercier", "staff", "restaurant"),
    _p("staff-resto-10", "staff.restaurant.10@example.com", "Axel", "Fournier", "staff", "restaurant"),
    _p("staff-resto-11", "staff.restaurant.11@example.com", "Maya", "Girard", "staff", "restaurant"),
    _p("mgr-maint-1", "mgr.maintenance.demo@example.com", "Thomas", "Girard", "manager", "maintenance", persona=True, badge=True),
    _p("mgr-maint-2", "mgr.maintenance.2@example.com", "Céline", "Dupuis", "manager", "maintenance", badge=True),
    _p("staff-maint-1", "staff.maintenance.1@example.com", "Rayan", "Lemoine", "staff", "maintenance", badge=True),
    _p("staff-maint-2", "staff.maintenance.2@example.com", "Clara", "Riviere", "staff", "maintenance"),
    _p("staff-maint-3", "staff.maintenance.3@example.com", "Noah", "Denis", "staff", "maintenance"),
    _p("staff-maint-4", "staff.maintenance.4@example.com", "Emma", "Chevalier", "staff", "maintenance"),
    _p("staff-maint-5", "staff.maintenance.5@example.com", "Léo", "Brun", "staff", "maintenance"),
    _p("staff-maint-6", "staff.maintenance.6@example.com", "Alice", "Clement", "staff", "maintenance"),
    _p("mgr-comm-1", "mgr.communication.demo@example.com", "Clara", "Petit", "manager", "communication", secondary="evenements_privatisations", persona=True, badge=True),
    _p("mgr-comm-2", "mgr.communication.2@example.com", "Juliette", "Aubert", "manager", "communication"),
    _p("staff-comm-1", "staff.communication.1@example.com", "Sacha", "Lemoine", "staff", "communication", badge=True),
    _p("staff-comm-2", "staff.communication.2@example.com", "Nina", "Perrot", "staff", "communication"),
    _p("staff-comm-3", "staff.communication.3@example.com", "Eliott", "Robin", "staff", "communication"),
    _p("mgr-events-1", "mgr.events.demo@example.com", "Hugo", "Renard", "manager", "evenements_privatisations", secondary="communication", persona=True, badge=True),
    _p("mgr-events-2", "mgr.events.2@example.com", "Marine", "Blanchard", "manager", "evenements_privatisations", secondary="restaurant", badge=True),
    _p("staff-events-1", "staff.events.1@example.com", "Théo", "Garnier", "staff", "evenements_privatisations", badge=True),
    _p("staff-events-2", "staff.events.2@example.com", "Louise", "Faivre", "staff", "evenements_privatisations"),
    _p("staff-events-3", "staff.events.3@example.com", "Noé", "Masson", "staff", "evenements_privatisations"),
    _p("staff-events-4", "staff.events.4@example.com", "Agathe", "Picard", "staff", "evenements_privatisations"),
    _p("mgr-rh-1", "mgr.rh.demo@example.com", "Marine", "Dufour", "manager", "rh", persona=True, badge=True),
    _p("mgr-rh-2", "mgr.rh.2@example.com", "Pierre", "Benoit", "manager", "rh"),
    _p("staff-rh-1", "staff.rh.1@example.com", "Léonie", "Meyer", "staff", "rh", badge=True),
    _p("staff-rh-2", "staff.rh.2@example.com", "Ilan", "David", "staff", "rh"),
    _p("staff-rh-3", "staff.rh.3@example.com", "Capucine", "Adam", "staff", "rh"),
    _p("ex-hotel-1", "ex.hotel.1@example.com", "Olivier", "Paris", "staff", "hotel", status="deactivated", deactivate_on="2026-06-15"),
    _p("ex-resto-1", "ex.resto.1@example.com", "Nadia", "Leroux", "staff", "restaurant", status="deactivated", deactivate_on="2026-05-20"),
    _p("ex-maint-1", "ex.maint.1@example.com", "Karim", "Benoit", "staff", "maintenance", status="deactivated", deactivate_on="2026-04-10"),
    _p("ex-comm-1", "ex.comm.1@example.com", "Fanny", "Olivier", "manager", "communication", status="deactivated", deactivate_on="2026-07-02"),
    _p("invite-hotel-1", "invite.hotel.1@example.com", "Arthur", "Klein", "staff", "hotel", status="invited"),
    _p("invite-rh-1", "invite.rh.1@example.com", "Mélanie", "Schneider", "staff", "rh", status="invited"),
)


def validate_roster() -> list[str]:
    errors: list[str] = []
    emails = [person.email for person in ROSTER]
    if len(emails) != len(set(emails)):
        errors.append("roster emails are not unique")
    active = [p for p in ROSTER if p.status == "active"]
    deactivated = [p for p in ROSTER if p.status == "deactivated"]
    invited = [p for p in ROSTER if p.status == "invited"]
    if len(active) != 60:
        errors.append(f"expected 60 fictive actives, got {len(active)}")
    if len(deactivated) != 4:
        errors.append(f"expected 4 deactivated, got {len(deactivated)}")
    if len(invited) != 2:
        errors.append(f"expected 2 invited, got {len(invited)}")
    if sum(1 for p in ROSTER if p.persona) != 10:
        errors.append("expected 10 personas")
    if sum(1 for p in active if p.secondary_pole) != 5:
        errors.append("expected 5 multi-scope actives")
    if sum(1 for p in ROSTER if p.badge_eligible) != 21:
        errors.append("expected 21 badge-eligible members")
    directors = [p for p in active if p.role == "director"]
    managers = [p for p in active if p.role == "manager"]
    staff = [p for p in active if p.role == "staff"]
    if len(directors) != 1 or len(managers) != 18 or len(staff) != 41:
        errors.append(
            f"active role split {len(directors)}/{len(managers)}/{len(staff)} != 1/18/41"
        )
    return errors
