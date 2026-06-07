from django.db import migrations, models
import django.db.models.deletion
import uuid


def reseed_catalog_from_arborescence(apps, schema_editor):
    from houston.establishments.legacy_onboarding_catalog_seed import (
        catalog_domain_rows,
        catalog_module_rows,
        catalog_subject_rows,
    )

    OnboardingCatalogModule = apps.get_model("establishments", "OnboardingCatalogModule")
    OnboardingCatalogDomain = apps.get_model("establishments", "OnboardingCatalogDomain")
    OnboardingCatalogSubject = apps.get_model("establishments", "OnboardingCatalogSubject")

    OnboardingCatalogSubject.objects.all().delete()
    OnboardingCatalogDomain.objects.all().delete()
    OnboardingCatalogModule.objects.all().delete()

    module_by_key: dict[str, object] = {}
    sort = 10
    for row in catalog_module_rows():
        module, _ = OnboardingCatalogModule.objects.update_or_create(
            key=row["key"],
            defaults={
                "label": row["label"],
                "description": "",
                "active": True,
                "sort_order": sort,
            },
        )
        module_by_key[row["key"]] = module
        sort += 10

    domain_by_key: dict[str, object] = {}
    sort = 10
    for row in catalog_domain_rows():
        module = module_by_key[row["module_key"]]
        domain, _ = OnboardingCatalogDomain.objects.update_or_create(
            key=row["key"],
            defaults={
                "catalog_module": module,
                "label": row["label"],
                "description": "",
                "active": True,
                "sort_order": sort,
            },
        )
        domain_by_key[row["key"]] = domain
        sort += 10

    sort = 10
    for row in catalog_subject_rows():
        domain = domain_by_key[row["domain_key"]]
        OnboardingCatalogSubject.objects.update_or_create(
            key=row["key"],
            defaults={
                "catalog_domain": domain,
                "label": row["label"],
                "description": "",
                "active": True,
                "sort_order": sort,
            },
        )
        sort += 10


def deactivate_legacy_runtime_domains(apps, schema_editor):
    OperationalDomain = apps.get_model("establishments", "OperationalDomain")
    OnboardingCatalogDomain = apps.get_model("establishments", "OnboardingCatalogDomain")
    valid_keys = set(OnboardingCatalogDomain.objects.values_list("key", flat=True))
    OperationalDomain.objects.exclude(key__in=valid_keys).update(active=False)


class Migration(migrations.Migration):
    dependencies = [
        (
            "establishments",
            "0006_operationaldomain_managed_by_onboarding_proposal_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="OnboardingCatalogSubject",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("key", models.CharField(max_length=150, unique=True)),
                ("label", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                "ordering": ["sort_order", "key"],
            },
        ),
        migrations.AddField(
            model_name="onboardingcatalogdomain",
            name="catalog_module",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="catalog_domains",
                to="establishments.onboardingcatalogmodule",
            ),
        ),
        migrations.AlterField(
            model_name="onboardingcatalogdomain",
            name="key",
            field=models.CharField(max_length=120, unique=True),
        ),
        migrations.AddField(
            model_name="operationaldomain",
            name="operational_module",
            field=models.ForeignKey(
                blank=True,
                db_index=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="operational_domains",
                to="establishments.operationalmodule",
            ),
        ),
        migrations.AlterField(
            model_name="operationaldomain",
            name="key",
            field=models.CharField(max_length=120),
        ),
        migrations.CreateModel(
            name="OperationalSubject",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("key", models.CharField(max_length=150)),
                ("label", models.CharField(max_length=255)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("ai_proposed", "AI Proposed"),
                            ("manual", "Manual"),
                            ("template", "Template"),
                        ],
                        default="manual",
                        max_length=20,
                    ),
                ),
                ("active", models.BooleanField(default=True)),
                (
                    "establishment",
                    models.ForeignKey(
                        db_index=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="operational_subjects",
                        to="establishments.establishment",
                    ),
                ),
                (
                    "managed_by_onboarding_proposal",
                    models.ForeignKey(
                        blank=True,
                        db_index=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="managed_operational_subjects",
                        to="establishments.onboardingproposal",
                    ),
                ),
                (
                    "operational_domain",
                    models.ForeignKey(
                        blank=True,
                        db_index=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="operational_subjects",
                        to="establishments.operationaldomain",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="onboardingcatalogsubject",
            name="catalog_domain",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="catalog_subjects",
                to="establishments.onboardingcatalogdomain",
            ),
        ),
        migrations.AddIndex(
            model_name="onboardingcatalogsubject",
            index=models.Index(fields=["active"], name="onbrd_cat_subj_active_idx"),
        ),
        migrations.AddIndex(
            model_name="onboardingcatalogsubject",
            index=models.Index(
                fields=["active", "sort_order", "key"],
                name="onbrd_cat_subj_order_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="onboardingcatalogsubject",
            index=models.Index(fields=["catalog_domain"], name="onbrd_cat_subj_dom_idx"),
        ),
        migrations.AddIndex(
            model_name="operationaldomain",
            index=models.Index(fields=["operational_module"], name="domain_op_module_idx"),
        ),
        migrations.AddIndex(
            model_name="operationalsubject",
            index=models.Index(fields=["establishment"], name="subject_est_idx"),
        ),
        migrations.AddIndex(
            model_name="operationalsubject",
            index=models.Index(fields=["establishment", "active"], name="subject_est_active_idx"),
        ),
        migrations.AddIndex(
            model_name="operationalsubject",
            index=models.Index(fields=["key"], name="subject_key_idx"),
        ),
        migrations.AddIndex(
            model_name="operationalsubject",
            index=models.Index(
                fields=["managed_by_onboarding_proposal"],
                name="subject_managed_prop_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="operationalsubject",
            index=models.Index(fields=["operational_domain"], name="subject_op_domain_idx"),
        ),
        migrations.AddConstraint(
            model_name="operationalsubject",
            constraint=models.UniqueConstraint(
                fields=("establishment", "key"),
                name="op_subject_est_key_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="onboardingcatalogdomain",
            index=models.Index(fields=["catalog_module"], name="onbrd_cat_domain_mod_idx"),
        ),
        migrations.RunPython(reseed_catalog_from_arborescence, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="onboardingcatalogdomain",
            name="catalog_module",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="catalog_domains",
                to="establishments.onboardingcatalogmodule",
            ),
        ),
        migrations.RunPython(deactivate_legacy_runtime_domains, migrations.RunPython.noop),
    ]
