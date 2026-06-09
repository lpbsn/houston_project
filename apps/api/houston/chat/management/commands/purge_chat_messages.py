from __future__ import annotations

import uuid

from django.core.management.base import BaseCommand, CommandError
from houston.chat.purge import purge_chat_messages


class Command(BaseCommand):
    help = "Purges chat messages older than the configured retention window."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count messages that would be deleted without deleting them.",
        )
        parser.add_argument(
            "--establishment-id",
            type=str,
            default=None,
            help="Limit purge to one establishment UUID.",
        )

    def handle(self, *args, **options):
        establishment_id = options.get("establishment_id")
        parsed_establishment_id = None
        if establishment_id:
            try:
                parsed_establishment_id = uuid.UUID(str(establishment_id))
            except ValueError as exc:
                raise CommandError("Invalid establishment id.") from exc

        result = purge_chat_messages(
            establishment_id=parsed_establishment_id,
            dry_run=bool(options.get("dry_run")),
        )

        if result.dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run: {result.deleted_count} chat message(s) would be purged.",
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Purged {result.deleted_count} chat message(s) in {result.batch_count} batch(es).",
            )
        )
