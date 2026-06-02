from __future__ import annotations

from django.core.management.base import BaseCommand

from houston.uploads.services import cleanup_expired_uploads


class Command(BaseCommand):
    help = "Deletes expired unlinked temporary photo uploads."

    def handle(self, *args, **options):
        deleted_count = cleanup_expired_uploads()
        self.stdout.write(self.style.SUCCESS(f"Cleaned up {deleted_count} expired upload(s)."))
