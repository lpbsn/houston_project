from django.core.management.base import BaseCommand, CommandError

from houston.platform.services import resolve_user_by_identifier, revoke_platform_operator


class Command(BaseCommand):
    help = "Revoke Spore Platform operator access without changing tenant memberships."

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
        access = revoke_platform_operator(user=user)
        if access is None:
            self.stdout.write(
                self.style.SUCCESS(
                    f"No platform operator access record for {user.pk}."
                )
            )
            return
        self.stdout.write(
            self.style.SUCCESS(f"Platform operator access is inactive for {user.pk}.")
        )
