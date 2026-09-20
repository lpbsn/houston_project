from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0006_remove_aiusagelog_onboarding_proposal"),
        ("establishments", "0035_membership_scope_same_establishment"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="operationalunit",
            name="unit_managed_prop_idx",
        ),
        migrations.RemoveField(
            model_name="activitysubject",
            name="managed_by_onboarding_proposal",
        ),
        migrations.RemoveField(
            model_name="businessunit",
            name="managed_by_onboarding_proposal",
        ),
        migrations.RemoveField(
            model_name="operationalunit",
            name="managed_by_onboarding_proposal",
        ),
        migrations.DeleteModel(
            name="OnboardingProposal",
        ),
    ]
