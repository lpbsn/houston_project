from django.db import migrations, models
from django.db.models import Q


def _assert_no_custom_prefix_catalog_subject_keys(apps, schema_editor):
    CatalogActivitySubject = apps.get_model("establishments", "CatalogActivitySubject")
    invalid_keys = list(
        CatalogActivitySubject.objects.filter(key__startswith="custom--")
        .order_by("key")
        .values_list("key", flat=True)
    )
    if invalid_keys:
        joined = ", ".join(invalid_keys)
        raise RuntimeError(
            "Cannot add catalog_activity_subject_key_no_custom_prefix_ck: "
            f"existing CatalogActivitySubject keys use reserved prefix custom--: {joined}"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0021_establishmentmembership_push_enabled"),
    ]

    operations = [
        migrations.RenameField(
            model_name="catalogbusinessunit",
            old_name="default_unit_type",
            new_name="unit_type",
        ),
        migrations.RunPython(
            _assert_no_custom_prefix_catalog_subject_keys,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="catalogactivitysubject",
            constraint=models.CheckConstraint(
                condition=~Q(key__startswith="custom--"),
                name="catalog_activity_subject_key_no_custom_prefix_ck",
            ),
        ),
        migrations.DeleteModel(
            name="OnboardingCatalogUnit",
        ),
    ]
