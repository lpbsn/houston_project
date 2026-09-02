from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0031_membershipblock_contentreport"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contentreport",
            name="content_kind",
            field=models.CharField(
                choices=[
                    ("observation", "Observation"),
                    ("comment", "Comment"),
                    ("chat_message", "Chat message"),
                    ("user", "User"),
                ],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="contentreport",
            name="status",
            field=models.CharField(
                choices=[("open", "Open"), ("acknowledged", "Acknowledged")],
                default="open",
                max_length=20,
            ),
        ),
    ]
