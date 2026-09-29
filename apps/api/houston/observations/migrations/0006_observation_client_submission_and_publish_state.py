import uuid

from django.db import migrations, models


def _backfill_client_submission_ids(apps, schema_editor):
    Observation = apps.get_model("observations", "Observation")
    pending = Observation.objects.filter(client_submission_id__isnull=True).iterator()
    for observation in pending:
        Observation.objects.filter(pk=observation.pk).update(client_submission_id=uuid.uuid4())


class Migration(migrations.Migration):
    dependencies = [
        ("observations", "0005_action_plan_task_observation"),
    ]

    operations = [
        migrations.AddField(
            model_name="observation",
            name="client_submission_id",
            field=models.UUIDField(null=True),
        ),
        migrations.RunPython(
            _backfill_client_submission_ids,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="observation",
            name="client_submission_id",
            field=models.UUIDField(),
        ),
        migrations.AddConstraint(
            model_name="observation",
            constraint=models.UniqueConstraint(
                fields=(
                    "establishment",
                    "submitted_by_membership",
                    "client_submission_id",
                ),
                name="observation_client_submission_uniq",
            ),
        ),
        migrations.AddField(
            model_name="observationprocessing",
            name="published_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="observationprocessing",
            name="next_retry_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="observationprocessing",
            index=models.Index(
                fields=["status", "published_at"],
                name="obs_processing_published_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="observationprocessing",
            index=models.Index(
                fields=["status", "next_retry_at"],
                name="obs_processing_retry_at_idx",
            ),
        ),
    ]
