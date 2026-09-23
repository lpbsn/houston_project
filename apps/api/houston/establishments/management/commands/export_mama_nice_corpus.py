from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.mama_nice_dataset_export import write_mama_nice_corpus_export
from houston.establishments.mama_nice_dataset_sample_export import write_mama_nice_sample_export


class Command(BaseCommand):
    help = (
        "Export Mama Nice corpus markdown. --sample writes the editorial sample only. "
        "Does not write to the database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            dest="output_dir",
            default="var/mama_nice_corpus_export",
        )
        parser.add_argument(
            "--sample",
            action="store_true",
            help="Export the editorial sample only. Does not compile the 420-signal corpus.",
        )

    def handle(self, *args, **options):
        directory = Path(options["output_dir"])
        try:
            if options["sample"]:
                written = write_mama_nice_sample_export(directory)
            else:
                written = write_mama_nice_corpus_export(directory)
        except MamaNiceDatasetError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(written)} files to {directory}."))
