from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0037_mamaniceseedrecord"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="mamaniceseedrecord",
            name="mama_nice_seed_est_type_object_uniq",
        ),
        migrations.AddConstraint(
            model_name="mamaniceseedrecord",
            constraint=models.UniqueConstraint(
                fields=("establishment", "object_type", "object_id", "event_kind"),
                name="mama_nice_seed_est_type_object_kind_uniq",
            ),
        ),
    ]
