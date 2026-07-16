from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("establishments", "0025_bu_as_identity_harden"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="businessunit",
            name="bu_est_key_uniq",
        ),
        migrations.RemoveIndex(
            model_name="businessunit",
            name="bu_est_type_idx",
        ),
        migrations.RemoveIndex(
            model_name="businessunit",
            name="bu_key_idx",
        ),
        migrations.RemoveField(
            model_name="businessunit",
            name="key",
        ),
        migrations.RemoveField(
            model_name="businessunit",
            name="label",
        ),
        migrations.RemoveField(
            model_name="businessunit",
            name="description",
        ),
        migrations.RemoveField(
            model_name="businessunit",
            name="unit_type",
        ),
    ]
