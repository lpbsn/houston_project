# Defensive cleanup for orphan legacy taxonomy tables removed in 0016.
# Idempotent: safe on clean DBs; heals stale volumes where DeleteModel left orphans.

from django.db import migrations

_LEGACY_TAXONOMY_TABLES = (
    "establishments_routinghintdomain",
    "establishments_routinghint",
    "establishments_runtimetagdomain",
    "establishments_runtimetag",
    "establishments_runtimevocabulary",
    "establishments_operationalsubject",
    "establishments_operationaldomain",
    "establishments_operationalmodule",
    "establishments_taxonomymigrationmap",
    "establishments_onboardingcatalogsubject",
    "establishments_onboardingcatalogdomain",
    "establishments_onboardingcatalogmodule",
)

_DROP_LEGACY_TABLES_SQL = "\n".join(
    f"DROP TABLE IF EXISTS {table} CASCADE;"
    for table in _LEGACY_TAXONOMY_TABLES
)


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0018_establishment_chat_enabled"),
    ]

    operations = [
        migrations.RunSQL(
            sql=_DROP_LEGACY_TABLES_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
