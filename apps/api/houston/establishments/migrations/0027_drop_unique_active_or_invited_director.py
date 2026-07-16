from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("establishments", "0026_drop_bu_legacy_columns"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="establishmentmembership",
            name="unique_active_or_invited_director_per_establishment",
        ),
    ]
