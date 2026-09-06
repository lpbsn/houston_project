from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_user_legal_consent_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="ai_declined_version",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]
