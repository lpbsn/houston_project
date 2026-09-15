from django.db import migrations


def clamp_push_when_in_app_disabled(apps, schema_editor):
    EstablishmentMembership = apps.get_model("establishments", "EstablishmentMembership")
    EstablishmentMembership.objects.filter(notifications_enabled=False).update(
        push_enabled=False,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0033_establishment_name_nullable_non_draft_requires_name"),
    ]

    operations = [
        migrations.RunPython(clamp_push_when_in_app_disabled, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="establishmentmembership",
            name="notifications_enabled",
        ),
    ]
