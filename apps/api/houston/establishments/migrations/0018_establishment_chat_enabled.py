from django.db import migrations, models


def enable_chat_for_active_establishments(apps, schema_editor):
    Establishment = apps.get_model("establishments", "Establishment")
    Establishment.objects.filter(status="active").update(chat_enabled=True)


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0017_establishment_timezone"),
    ]

    operations = [
        migrations.AddField(
            model_name="establishment",
            name="chat_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            enable_chat_for_active_establishments,
            migrations.RunPython.noop,
        ),
    ]
