from django.db import migrations, models
from django.db.models import Count


def _assert_no_duplicate_active_aggregation_keys(apps, schema_editor):
    Signal = apps.get_model("signals", "Signal")
    duplicate_groups = (
        Signal.objects.filter(status__in=["open", "in_progress"])
        .values(
            "establishment_id",
            "affected_business_unit_id",
            "responsible_business_unit_id",
            "activity_subject_id",
            "operational_unit_id",
            "issue_focus",
        )
        .annotate(signal_count=Count("id"))
        .filter(signal_count__gt=1)
    )
    sample = list(duplicate_groups[:5])
    if sample:
        total = duplicate_groups.count()
        raise RuntimeError(
            "Cannot add signal_unique_active_aggregation_key: "
            f"found {total} duplicate active aggregation key group(s). "
            f"Sample: {sample}"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("signals", "0005_signal_issue_focus"),
    ]

    operations = [
        migrations.RunPython(
            _assert_no_duplicate_active_aggregation_keys,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="signal",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status__in", frozenset({"in_progress", "open"}))),
                fields=(
                    "establishment",
                    "affected_business_unit",
                    "responsible_business_unit",
                    "activity_subject",
                    "operational_unit",
                    "issue_focus",
                ),
                name="signal_unique_active_aggregation_key",
                nulls_distinct=False,
            ),
        ),
    ]
