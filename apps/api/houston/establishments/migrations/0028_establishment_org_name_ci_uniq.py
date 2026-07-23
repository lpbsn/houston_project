from __future__ import annotations

from django.db import migrations, models
from django.db.models.functions import Lower, Trim


ESTABLISHMENT_ORG_NAME_CI_UNIQ = "establishment_org_name_ci_uniq"


def _fail_on_duplicate_establishment_names(apps, schema_editor):
    Establishment = apps.get_model("establishments", "Establishment")
    duplicates = (
        Establishment.objects.annotate(name_key=Lower(Trim("name")))
        .values("organization_id", "name_key")
        .annotate(count=models.Count("id"))
        .filter(count__gt=1)
        .order_by("organization_id", "name_key")
    )
    collisions = list(duplicates)
    if not collisions:
        return

    lines = [
        "Cannot add establishment_org_name_ci_uniq: resolve duplicate "
        "establishment names (case-insensitive, trimmed) per organization:"
    ]
    for row in collisions:
        lines.append(
            f"  organization_id={row['organization_id']} "
            f"name_key={row['name_key']!r} count={row['count']}"
        )
    raise RuntimeError("\n".join(lines))


class Migration(migrations.Migration):

    dependencies = [
        ("establishments", "0027_drop_unique_active_or_invited_director"),
    ]

    operations = [
        migrations.RunPython(
            _fail_on_duplicate_establishment_names,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="establishment",
            constraint=models.UniqueConstraint(
                Lower(Trim("name")),
                "organization",
                name=ESTABLISHMENT_ORG_NAME_CI_UNIQ,
            ),
        ),
    ]
