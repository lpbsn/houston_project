# Generated manually for Lot 6 legacy cleanup.

import django.db.models.deletion
from django.db import migrations, models


def delete_legacy_membership_scopes(apps, schema_editor):
    MembershipScope = apps.get_model("establishments", "MembershipScope")
    MembershipScope.objects.filter(business_unit__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0015_runtime_vocabulary_business_unit"),
        ("signals", "0004_remove_legacy_operational_taxonomy_fks"),
        ("actions", "0004_remove_legacy_operational_taxonomy_fks"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="membershipscope",
            name="membership_scope_business_unit_uniq",
        ),
        migrations.RemoveConstraint(
            model_name="membershipscope",
            name="membership_scope_exactly_one_target",
        ),
        migrations.RemoveConstraint(
            model_name="membershipscope",
            name="membership_scope_module_uniq",
        ),
        migrations.RemoveConstraint(
            model_name="membershipscope",
            name="membership_scope_domain_uniq",
        ),
        migrations.RemoveConstraint(
            model_name="membershipscope",
            name="membership_scope_subject_uniq",
        ),
        migrations.RemoveIndex(
            model_name="membershipscope",
            name="mship_scope_module_idx",
        ),
        migrations.RemoveIndex(
            model_name="membershipscope",
            name="mship_scope_domain_idx",
        ),
        migrations.RemoveIndex(
            model_name="membershipscope",
            name="mship_scope_subject_idx",
        ),
        migrations.RunPython(delete_legacy_membership_scopes, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="membershipscope",
            name="operational_module",
        ),
        migrations.RemoveField(
            model_name="membershipscope",
            name="operational_domain",
        ),
        migrations.RemoveField(
            model_name="membershipscope",
            name="operational_subject",
        ),
        migrations.AlterField(
            model_name="membershipscope",
            name="business_unit",
            field=models.ForeignKey(
                db_index=False,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="membership_scopes",
                to="establishments.businessunit",
            ),
        ),
        migrations.AddConstraint(
            model_name="membershipscope",
            constraint=models.UniqueConstraint(
                fields=("membership", "business_unit"),
                name="membership_scope_business_unit_uniq",
            ),
        ),
        migrations.DeleteModel(
            name="RuntimeTagDomain",
        ),
        migrations.DeleteModel(
            name="RoutingHintDomain",
        ),
        migrations.DeleteModel(
            name="RuntimeTag",
        ),
        migrations.DeleteModel(
            name="RoutingHint",
        ),
        migrations.DeleteModel(
            name="RuntimeVocabulary",
        ),
        migrations.DeleteModel(
            name="OperationalSubject",
        ),
        migrations.DeleteModel(
            name="OperationalDomain",
        ),
        migrations.DeleteModel(
            name="OperationalModule",
        ),
        migrations.DeleteModel(
            name="TaxonomyMigrationMap",
        ),
        migrations.DeleteModel(
            name="OnboardingCatalogSubject",
        ),
        migrations.DeleteModel(
            name="OnboardingCatalogDomain",
        ),
        migrations.DeleteModel(
            name="OnboardingCatalogModule",
        ),
    ]
