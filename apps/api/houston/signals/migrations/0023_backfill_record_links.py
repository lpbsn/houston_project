from zoneinfo import ZoneInfo

from django.db import migrations
from django.db.models import Max


def forwards(apps, schema_editor):
    Signal = apps.get_model("signals", "Signal")
    Link = apps.get_model("signals", "SignalExecutionLink")
    Execution = apps.get_model("action_plans", "ActionPlanExecution")
    db = schema_editor.connection.alias
    for execution in (
        Execution.objects.using(db)
        .select_related("establishment")
        .order_by("id")
        .iterator(chunk_size=250)
    ):
        if Link.objects.using(db).filter(execution_id=execution.id).exists():
            continue
        if execution.source_signal_id:
            signal_id = execution.source_signal_id
        else:
            terminal = execution.status in ("done", "canceled")
            signal = Signal.objects.using(db).create(
                establishment_id=execution.establishment_id,
                record_kind="project",
                routing_status="unassigned",
                title=execution.title,
                structured_summary=execution.description,
                affected_business_unit_id=execution.pilot_business_unit_id,
                responsible_business_unit_id=execution.pilot_business_unit_id,
                owner_membership_id=execution.chronology_owner_membership_id
                or execution.created_by_id,
                status="canceled" if terminal else "in_progress",
                closure_reason="acknowledged"
                if execution.status == "done"
                else "abandoned"
                if terminal
                else "",
                canceled_at=(
                    execution.validated_at
                    or execution.marked_done_at
                    or execution.canceled_at
                    or execution.updated_at
                )
                if terminal
                else None,
                last_activity_at=execution.last_activity_at,
                due_on=execution.end_at.astimezone(
                    ZoneInfo(execution.establishment.timezone)
                ).date()
                if execution.end_at
                else None,
            )
            Signal.objects.using(db).filter(pk=signal.id).update(created_at=execution.created_at)
            signal_id = signal.id
        Link.objects.using(db).create(
            signal_id=signal_id, execution_id=execution.id, added_by_id=execution.created_by_id
        )
    # Date adoption is limited to records with existing executions; no invented deadline.
    for signal in (
        Signal.objects.using(db)
        .filter(record_kind="observation", due_on__isnull=True)
        .select_related("establishment")
        .iterator(chunk_size=250)
    ):
        end = (
            Execution.objects.using(db)
            .filter(source_signal_id=signal.id)
            .aggregate(last=Max("end_at"))["last"]
        )
        if end:
            Signal.objects.using(db).filter(pk=signal.id).update(
                due_on=end.astimezone(ZoneInfo(signal.establishment.timezone)).date()
            )
    Signal.objects.using(db).filter(status="resolved", closure_reason="").update(
        closure_reason="resolved"
    )
    Signal.objects.using(db).filter(status="canceled", closure_reason="").update(
        closure_reason="abandoned"
    )


class Migration(migrations.Migration):
    dependencies = [("signals", "0022_signal_merged_into")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
