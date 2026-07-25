from django.db import migrations
from django.db.models import F, Q


def _backfill_signal_routing_status(apps, schema_editor):
    Signal = apps.get_model("signals", "Signal")
    coherent = (
        Q(affected_business_unit_id__isnull=False)
        & Q(responsible_business_unit_id__isnull=False)
        & Q(activity_subject_id__isnull=False)
        & Q(activity_subject__business_unit_id=F("responsible_business_unit_id"))
    )
    Signal.objects.filter(coherent).update(routing_status="resolved")
    Signal.objects.exclude(coherent).update(routing_status="unassigned")


def _noop_reverse(apps, schema_editor):
    Signal = apps.get_model("signals", "Signal")
    Signal.objects.all().update(routing_status=None)


class Migration(migrations.Migration):
    dependencies = [
        ("signals", "0008_signal_routing_status_nullable_and_v6_fields"),
    ]

    operations = [
        migrations.RunPython(
            _backfill_signal_routing_status,
            _noop_reverse,
        ),
    ]
