import re

from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


def _slugify_label(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.replace("œ", "oe").replace("æ", "ae")
    normalized = re.sub(r"[^\w\s-]", "", normalized, flags=re.UNICODE)
    normalized = re.sub(r"[-\s]+", "_", normalized)
    return normalized.strip("_")


def _build_bu_routing_key(*, business_unit_id, catalog_key: str, specific_name: str) -> str:
    specific_slug = _slugify_label(specific_name).replace("_", "-")[:48]
    return f"{catalog_key}--{specific_slug}--{business_unit_id.hex[:16]}"


def _build_free_as_routing_key(*, activity_subject_id, label: str) -> str:
    label_slug = _slugify_label(label).replace("_", "-")[:64]
    return f"custom--{label_slug}--{activity_subject_id.hex[:16]}"


def forwards_backfill(apps, schema_editor):
    CatalogBusinessUnit = apps.get_model("establishments", "CatalogBusinessUnit")
    CatalogActivitySubject = apps.get_model("establishments", "CatalogActivitySubject")
    BusinessUnit = apps.get_model("establishments", "BusinessUnit")
    ActivitySubject = apps.get_model("establishments", "ActivitySubject")

    catalog_by_key = {row.key: row for row in CatalogBusinessUnit.objects.all()}
    catalog_as_by_key = {row.key: row for row in CatalogActivitySubject.objects.all()}

    unresolved_catalog_as = list(
        CatalogActivitySubject.objects.filter(catalog_business_unit__isnull=True).values_list(
            "id", "key"
        )
    )
    if unresolved_catalog_as:
        preview = ", ".join(f"{key}:{row_id}" for row_id, key in unresolved_catalog_as[:20])
        raise RuntimeError(
            "CatalogActivitySubject rows missing catalog_business_unit: " + preview
        )

    unresolved_bu = []
    for bu in BusinessUnit.objects.all().iterator():
        catalog = None
        if bu.catalog_business_unit_id:
            catalog = CatalogBusinessUnit.objects.filter(id=bu.catalog_business_unit_id).first()
        if catalog is None and bu.key:
            catalog = catalog_by_key.get(bu.key)
            if catalog is not None:
                bu.catalog_business_unit_id = catalog.id
        if catalog is None:
            unresolved_bu.append(str(bu.id))
            continue

        specific_name = (bu.specific_name or bu.label or bu.key or "").strip()
        if not specific_name:
            unresolved_bu.append(str(bu.id))
            continue
        normalized = (bu.normalized_specific_name or _slugify_label(specific_name)).strip()
        if not normalized:
            unresolved_bu.append(str(bu.id))
            continue
        routing_key = (bu.routing_key or "").strip()
        if not routing_key:
            routing_key = _build_bu_routing_key(
                business_unit_id=bu.id,
                catalog_key=catalog.key,
                specific_name=specific_name,
            )
        instance_description = (
            bu.instance_description
            if bu.instance_description is not None
            else (bu.description or "")
        )
        bu.specific_name = specific_name
        bu.normalized_specific_name = normalized
        bu.routing_key = routing_key
        bu.instance_description = instance_description or ""
        bu.save(
            update_fields=[
                "catalog_business_unit",
                "specific_name",
                "normalized_specific_name",
                "routing_key",
                "instance_description",
                "updated_at",
            ]
        )

    if unresolved_bu:
        preview = ", ".join(unresolved_bu[:20])
        raise RuntimeError(
            "BusinessUnit rows could not be backfilled (missing catalog/identity): "
            + preview
        )

    # Collision detection before hardening uniqueness.
    seen_norm: dict[tuple, list[str]] = {}
    seen_rk: dict[tuple, list[str]] = {}
    for bu in BusinessUnit.objects.all().only(
        "id", "establishment_id", "normalized_specific_name", "routing_key"
    ):
        seen_norm.setdefault(
            (bu.establishment_id, bu.normalized_specific_name), []
        ).append(str(bu.id))
        seen_rk.setdefault((bu.establishment_id, bu.routing_key), []).append(str(bu.id))
    norm_collisions = {k: v for k, v in seen_norm.items() if len(v) > 1}
    rk_collisions = {k: v for k, v in seen_rk.items() if len(v) > 1}
    if norm_collisions or rk_collisions:
        raise RuntimeError(
            "BusinessUnit identity collisions before hardening: "
            f"normalized={norm_collisions} routing_key={rk_collisions}"
        )

    unresolved_as = []
    for subject in ActivitySubject.objects.select_related(
        "catalog_activity_subject", "business_unit"
    ).iterator():
        catalog_as = None
        if subject.catalog_activity_subject_id:
            catalog_as = catalog_as_by_key.get(
                CatalogActivitySubject.objects.filter(id=subject.catalog_activity_subject_id)
                .values_list("key", flat=True)
                .first()
            )
            if catalog_as is None:
                catalog_as = CatalogActivitySubject.objects.filter(
                    id=subject.catalog_activity_subject_id
                ).first()

        if catalog_as is not None:
            routing_key = (subject.routing_key or catalog_as.key or "").strip()
            if not routing_key:
                unresolved_as.append(str(subject.id))
                continue
            subject.routing_key = routing_key
            subject.label = ""
            subject.description = ""
            subject.normalized_name = subject.normalized_name or _slugify_label(
                catalog_as.label
            )
            subject.save(
                update_fields=[
                    "routing_key",
                    "label",
                    "description",
                    "normalized_name",
                    "updated_at",
                ]
            )
            continue

        # Free subject
        label = (subject.label or "").strip()
        if not label:
            unresolved_as.append(str(subject.id))
            continue
        routing_key = (subject.routing_key or "").strip()
        if not routing_key:
            routing_key = _build_free_as_routing_key(
                activity_subject_id=subject.id,
                label=label,
            )
        if not routing_key.startswith("custom--"):
            # Force free prefix when no catalog FK.
            routing_key = _build_free_as_routing_key(
                activity_subject_id=subject.id,
                label=label,
            )
        subject.routing_key = routing_key
        subject.label = label
        subject.description = subject.description or ""
        subject.normalized_name = subject.normalized_name or _slugify_label(label)
        subject.save(
            update_fields=[
                "routing_key",
                "label",
                "description",
                "normalized_name",
                "updated_at",
            ]
        )

    if unresolved_as:
        preview = ", ".join(unresolved_as[:20])
        raise RuntimeError(
            "ActivitySubject rows could not be backfilled: " + preview
        )

    incomplete_bu = BusinessUnit.objects.filter(
        Q(specific_name__isnull=True)
        | Q(specific_name="")
        | Q(normalized_specific_name__isnull=True)
        | Q(normalized_specific_name="")
        | Q(routing_key__isnull=True)
        | Q(routing_key="")
        | Q(catalog_business_unit__isnull=True)
    ).count()
    if incomplete_bu:
        raise RuntimeError(
            f"{incomplete_bu} BusinessUnit row(s) still incomplete after backfill."
        )

    incomplete_as = ActivitySubject.objects.filter(
        Q(routing_key__isnull=True) | Q(routing_key="")
    ).count()
    if incomplete_as:
        raise RuntimeError(
            f"{incomplete_as} ActivitySubject row(s) still incomplete after backfill."
        )

    as_norm_collisions: dict[tuple, list[str]] = {}
    as_rk_collisions: dict[tuple, list[str]] = {}
    for subject in ActivitySubject.objects.all().only(
        "id", "business_unit_id", "normalized_name", "routing_key"
    ):
        as_norm_collisions.setdefault(
            (subject.business_unit_id, subject.normalized_name), []
        ).append(str(subject.id))
        as_rk_collisions.setdefault(
            (subject.business_unit_id, subject.routing_key), []
        ).append(str(subject.id))
    as_norm_collisions = {k: v for k, v in as_norm_collisions.items() if len(v) > 1}
    as_rk_collisions = {k: v for k, v in as_rk_collisions.items() if len(v) > 1}
    if as_norm_collisions or as_rk_collisions:
        raise RuntimeError(
            "ActivitySubject identity collisions before hardening: "
            f"normalized={as_norm_collisions} routing_key={as_rk_collisions}"
        )


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("establishments", "0024_process_onboarding_proposal_v3"),
    ]

    operations = [
        migrations.RunPython(forwards_backfill, backwards_noop),
        migrations.RemoveConstraint(
            model_name="businessunit",
            name="bu_est_normalized_specific_name_uniq",
        ),
        migrations.RemoveConstraint(
            model_name="businessunit",
            name="bu_est_routing_key_uniq",
        ),
        migrations.RemoveConstraint(
            model_name="activitysubject",
            name="activity_subject_bu_routing_key_uniq",
        ),
        migrations.AlterField(
            model_name="catalogactivitysubject",
            name="catalog_business_unit",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="catalog_activity_subjects",
                to="establishments.catalogbusinessunit",
            ),
        ),
        migrations.AlterField(
            model_name="businessunit",
            name="catalog_business_unit",
            field=models.ForeignKey(
                db_index=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="establishment_business_units",
                to="establishments.catalogbusinessunit",
            ),
        ),
        migrations.AlterField(
            model_name="businessunit",
            name="specific_name",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="businessunit",
            name="normalized_specific_name",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="businessunit",
            name="routing_key",
            field=models.CharField(max_length=180),
        ),
        migrations.AlterField(
            model_name="businessunit",
            name="instance_description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="activitysubject",
            name="catalog_activity_subject",
            field=models.ForeignKey(
                blank=True,
                db_index=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="establishment_activity_subjects",
                to="establishments.catalogactivitysubject",
            ),
        ),
        migrations.AlterField(
            model_name="activitysubject",
            name="routing_key",
            field=models.CharField(max_length=150),
        ),
        migrations.AlterField(
            model_name="activitysubject",
            name="label",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddConstraint(
            model_name="businessunit",
            constraint=models.UniqueConstraint(
                fields=("establishment", "normalized_specific_name"),
                name="bu_est_normalized_specific_name_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="businessunit",
            constraint=models.UniqueConstraint(
                fields=("establishment", "routing_key"),
                name="bu_est_routing_key_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="businessunit",
            constraint=models.CheckConstraint(
                condition=~models.Q(specific_name=""),
                name="bu_specific_name_nonempty_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="businessunit",
            constraint=models.CheckConstraint(
                condition=~models.Q(normalized_specific_name=""),
                name="bu_normalized_specific_name_nonempty_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="businessunit",
            constraint=models.CheckConstraint(
                condition=~models.Q(routing_key=""),
                name="bu_routing_key_nonempty_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="activitysubject",
            constraint=models.UniqueConstraint(
                fields=("business_unit", "routing_key"),
                name="activity_subject_bu_routing_key_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="activitysubject",
            constraint=models.CheckConstraint(
                condition=~models.Q(routing_key=""),
                name="as_routing_key_nonempty_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="activitysubject",
            constraint=models.CheckConstraint(
                condition=(
                    (
                        models.Q(catalog_activity_subject__isnull=False)
                        & models.Q(label="")
                        & models.Q(description="")
                        & ~models.Q(routing_key__startswith="custom--")
                    )
                    | (
                        models.Q(catalog_activity_subject__isnull=True)
                        & ~models.Q(label="")
                        & models.Q(routing_key__startswith="custom--")
                    )
                ),
                name="activity_subject_generic_or_free_ck",
            ),
        ),
    ]
