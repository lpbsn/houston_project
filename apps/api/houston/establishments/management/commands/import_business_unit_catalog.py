from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from houston.establishments.catalog_import import sync_catalog_from_normalized_rows
from houston.establishments.catalog_source_normalization import (
    activity_subjects_csv_path,
    business_units_csv_path,
    load_normalized_activity_subject_rows,
    load_normalized_business_unit_rows,
    normalize_catalog_from_source,
    suggestion_source_csv_path,
    write_normalized_catalog_csvs,
)


class Command(BaseCommand):
    help = (
        "Import versioned BusinessUnit / ActivitySubject catalogue seed CSVs "
        "into CatalogBusinessUnit and CatalogActivitySubject."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate seed files and print the report without writing to the database.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit with an error if validation warnings are present.",
        )
        parser.add_argument(
            "--regenerate-from-source",
            action="store_true",
            help="Rebuild normalized CSV seed files from suggestion_source.csv before import.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        strict = options["strict"]
        regenerate = options["regenerate_from_source"]

        if regenerate:
            source_path = suggestion_source_csv_path()
            if not source_path.exists():
                raise CommandError(f"Missing source catalogue file: {source_path}")
            catalog = normalize_catalog_from_source(path=source_path)
            write_normalized_catalog_csvs(catalog=catalog)
            self._print_report(catalog.report)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Regenerated seed CSVs: {business_units_csv_path()} "
                    f"and {activity_subjects_csv_path()}"
                )
            )
        else:
            catalog = None

        for path in (business_units_csv_path(), activity_subjects_csv_path()):
            if not path.exists():
                raise CommandError(
                    f"Missing normalized seed file: {path}. "
                    "Run with --regenerate-from-source first."
                )

        business_unit_rows = load_normalized_business_unit_rows()
        activity_subject_rows = load_normalized_activity_subject_rows()

        if catalog is None:
            self.stdout.write(
                f"Loaded {len(business_unit_rows)} business units and "
                f"{len(activity_subject_rows)} activity subjects from seed CSVs."
            )
        elif catalog.report.has_warnings:
            self._print_report(catalog.report)

        report = catalog.report if catalog is not None else None
        if report is None and strict:
            validation = normalize_catalog_from_source()
            report = validation.report
            if report.has_warnings:
                self._print_report(report)

        if strict and report is not None and report.has_warnings:
            raise CommandError("Catalog validation produced warnings (--strict).")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: no database changes applied."))
            return

        result = sync_catalog_from_normalized_rows(
            business_unit_rows=business_unit_rows,
            activity_subject_rows=activity_subject_rows,
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Catalog import complete: "
                f"BU created={result.business_units_created} "
                f"updated={result.business_units_updated}; "
                f"AS created={result.activity_subjects_created} "
                f"updated={result.activity_subjects_updated}"
            )
        )

    def _print_report(self, report) -> None:
        self.stdout.write(
            f"Catalog stats: {report.business_unit_count} business units, "
            f"{report.activity_subject_count} activity subjects"
        )
        if report.deduplicated_pairs:
            self.stdout.write("Deduplicated exact pairs:")
            for item in report.deduplicated_pairs:
                self.stdout.write(f"  - {item}")
        if report.quasi_duplicates:
            self.stdout.write("Quasi-duplicates:")
            for item in report.quasi_duplicates:
                self.stdout.write(f"  - {item}")
        if report.trimmed_labels:
            self.stdout.write(f"Trimmed labels: {len(report.trimmed_labels)}")
        for warning in report.warnings:
            self.stdout.write(self.style.WARNING(f"Warning: {warning}"))
