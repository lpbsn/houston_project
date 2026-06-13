from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signals", "0004_remove_legacy_operational_taxonomy_fks"),
    ]

    operations = [
        migrations.AddField(
            model_name="signal",
            name="issue_focus",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="candidatesignal",
            name="issue_focus",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
    ]
