from django.db import migrations, models


def assign_existing_colors(apps, schema_editor):
    BusinessUnit = apps.get_model("establishments", "BusinessUnit")
    # Bounded batches, one establishment at a time; inactive poles retain a slot.
    rows = BusinessUnit.objects.using(schema_editor.connection.alias).order_by(
        "establishment_id", "created_at", "id"
    )
    current_establishment = None
    color_index = 0
    batch = []
    for unit in rows.iterator(chunk_size=500):
        if unit.establishment_id != current_establishment:
            current_establishment = unit.establishment_id
            color_index = 0
        unit.color_index = color_index
        color_index += 1
        batch.append(unit)
        if len(batch) == 500:
            rows.bulk_update(batch, ["color_index"])
            batch = []
    if batch:
        rows.bulk_update(batch, ["color_index"])


class Migration(migrations.Migration):
    dependencies = [("establishments", "0039_mamaniceseedrecord_clock")]
    operations = [
        migrations.AddField(
            model_name="businessunit",
            name="color_index",
            field=models.PositiveIntegerField(null=True, blank=True, editable=False),
        ),
        migrations.RunPython(assign_existing_colors, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="businessunit",
            constraint=models.UniqueConstraint(
                fields=("establishment", "color_index"), name="bu_est_color_index_uniq"
            ),
        ),
    ]
