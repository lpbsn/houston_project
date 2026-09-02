from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_usersession_selected_establishment"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="ai_consent_version",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="ai_processing_consented_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="terms_accepted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="terms_version",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]
