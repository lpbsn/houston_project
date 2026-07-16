from django.db import migrations


def forwards(apps, schema_editor):
    from houston.establishments.onboarding_proposal_v3_migration import (
        assert_no_non_terminal_v3_proposals,
        process_non_terminal_v3_proposals,
    )

    process_non_terminal_v3_proposals(dry_run=False)
    assert_no_non_terminal_v3_proposals()


def backwards(apps, schema_editor):
    # Irreversible data migration (terminal history preserved intentionally).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("establishments", "0023_bu_as_lot2_identity"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
