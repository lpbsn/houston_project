from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0003_alter_aiusagelog_ai_domain"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="aiusagelog",
                    name="error_context",
                    field=models.JSONField(default=dict),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE ai_aiusagelog "
                        "ADD COLUMN IF NOT EXISTS error_context jsonb NOT NULL "
                        "DEFAULT '{}'::jsonb;"
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
