from django.core.management.base import BaseCommand, CommandError

from houston.accounts.models import User
from houston.platform.services import grant_platform_operator, resolve_user_by_identifier


class Command(BaseCommand):
    help = "Grant active Spore Platform operator access to an existing user."

    def add_arguments(self, parser):
        parser.add_argument(
            "identifier",
            help="User email or username.",
        )

    def handle(self, *args, **options):
        identifier = options["identifier"]
        user = resolve_user_by_identifier(identifier)
        if user is None:
            raise CommandError(f"No user found for identifier {identifier!r}.")
        if user.status != User.Status.ACTIVE:
            raise CommandError(
                f"User {identifier!r} is not active (status={user.status})."
            )
        access = grant_platform_operator(user=user)
        self.stdout.write(
            self.style.SUCCESS(
                f"Granted platform operator access to {user.pk} "
                f"(is_active={access.is_active})."
            )
        )
