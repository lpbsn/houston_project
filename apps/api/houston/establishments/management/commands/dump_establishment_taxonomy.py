from __future__ import annotations

import json
import uuid

from django.core.management.base import BaseCommand, CommandError

from houston.establishments.selectors import get_establishment_operational_taxonomy_snapshot


def format_taxonomy_snapshot_text(snapshot: dict) -> str:
    lines: list[str] = []
    establishment_id = snapshot["establishment_id"]
    establishment_name = snapshot["establishment_name"]
    lines.append(f"Establishment: {establishment_name} ({establishment_id})")
    lines.append("")

    modules = snapshot.get("modules") or []
    unassigned_domains = snapshot.get("unassigned_domains") or []
    units = snapshot.get("units") or []

    if not modules and not unassigned_domains and not units:
        lines.append("(no active operational taxonomy)")
        return "\n".join(lines)

    for module in modules:
        lines.append(f"[module] {module['key']} — {module['label']}")
        for domain in module.get("domains") or []:
            lines.append(f"  [domain] {domain['key']} — {domain['label']}")
            for subject in domain.get("subjects") or []:
                lines.append(f"    [subject] {subject['key']} — {subject['label']}")
        lines.append("")

    for domain in unassigned_domains:
        lines.append(f"[unassigned domain] {domain['key']} — {domain['label']}")
        for subject in domain.get("subjects") or []:
            lines.append(f"  [subject] {subject['key']} — {subject['label']}")
        lines.append("")

    if units:
        lines.append("[units] (establishment-level, orthogonal)")
        for unit in units:
            lines.append(f"  unit {unit['key']} — {unit['label']}")

    return "\n".join(lines).rstrip() + "\n"


class Command(BaseCommand):
    help = "Print the active operational taxonomy tree for an establishment."

    def add_arguments(self, parser):
        parser.add_argument(
            "establishment_id",
            help="Establishment UUID.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output the taxonomy snapshot as JSON.",
        )

    def handle(self, *args, **options):
        raw_establishment_id = options["establishment_id"]
        try:
            establishment_id = uuid.UUID(str(raw_establishment_id))
        except ValueError as exc:
            raise CommandError(
                f"Invalid establishment UUID: {raw_establishment_id}"
            ) from exc

        snapshot = get_establishment_operational_taxonomy_snapshot(
            establishment_id=establishment_id,
            active_only=True,
        )
        if snapshot is None:
            raise CommandError(f"Establishment not found: {establishment_id}")

        if options["json"]:
            self.stdout.write(json.dumps(snapshot, indent=2, default=str))
            return

        self.stdout.write(format_taxonomy_snapshot_text(snapshot))
