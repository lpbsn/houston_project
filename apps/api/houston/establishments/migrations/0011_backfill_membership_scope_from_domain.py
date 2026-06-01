from django.db import migrations


def forwards(apps, schema_editor):
    MembershipDomain = apps.get_model("establishments", "MembershipDomain")
    MembershipScope = apps.get_model("establishments", "MembershipScope")

    scopes_to_create = []
    for membership_domain in MembershipDomain.objects.select_related("operational_domain").iterator():
        scopes_to_create.append(
            MembershipScope(
                membership_id=membership_domain.membership_id,
                operational_domain_id=membership_domain.operational_domain_id,
            )
        )

    if scopes_to_create:
        MembershipScope.objects.bulk_create(scopes_to_create, ignore_conflicts=True)


def backwards(apps, schema_editor):
    MembershipScope = apps.get_model("establishments", "MembershipScope")
    MembershipScope.objects.filter(operational_domain__isnull=False).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("establishments", "0010_membership_scope"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
