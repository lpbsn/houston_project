from django.db import migrations, models


def populate_and_validate_semantic_aliases(apps, schema_editor):
    OperationalPattern = apps.get_model("analytics", "OperationalPattern")
    patterns = {
        pattern.id: pattern
        for pattern in OperationalPattern.objects.all().only(
            "id",
            "organization_id",
            "label",
            "normalized_label",
            "semantic_label",
            "normalized_semantic_label",
            "status",
            "merged_into_id",
        )
    }

    for pattern in patterns.values():
        semantic_label = pattern.semantic_label or pattern.label
        normalized_semantic_label = (
            pattern.normalized_semantic_label or pattern.normalized_label
        )
        OperationalPattern.objects.filter(pk=pattern.pk).update(
            semantic_label=semantic_label,
            normalized_semantic_label=normalized_semantic_label,
        )
        pattern.semantic_label = semantic_label
        pattern.normalized_semantic_label = normalized_semantic_label

    def terminal_active_target(pattern):
        seen = {pattern.id}
        current = pattern
        for _ in range(20):
            if current.status == "active":
                return current.id
            if current.status != "merged" or current.merged_into_id is None:
                return None
            target = patterns.get(current.merged_into_id)
            if target is None:
                return None
            if target.id in seen:
                return None
            if target.organization_id != pattern.organization_id:
                return None
            seen.add(target.id)
            current = target
        return None

    aliases = {}
    for pattern in patterns.values():
        if pattern.status not in {"active", "merged"}:
            continue
        key = (pattern.organization_id, pattern.normalized_semantic_label)
        aliases.setdefault(key, []).append(pattern)

    errors = []
    for (organization_id, normalized_alias), grouped_patterns in aliases.items():
        target_ids = set()
        for pattern in grouped_patterns:
            target_id = terminal_active_target(pattern)
            if target_id is None:
                errors.append(
                    f"organization={organization_id} alias={normalized_alias!r} "
                    f"pattern={pattern.id} does not resolve to an active terminal target"
                )
                continue
            target_ids.add(target_id)
        if len(target_ids) > 1:
            errors.append(
                f"organization={organization_id} alias={normalized_alias!r} "
                f"resolves to multiple active targets: {sorted(str(id) for id in target_ids)}"
            )

    if errors:
        raise RuntimeError(
            "Cannot migrate analytics pattern semantic aliases:\n" + "\n".join(errors)
        )


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0004_pattern_lifecycle_split_event"),
    ]

    operations = [
        migrations.AddField(
            model_name="operationalpattern",
            name="semantic_label",
            field=models.CharField(blank=True, default="", max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="operationalpattern",
            name="normalized_semantic_label",
            field=models.CharField(blank=True, default="", editable=False, max_length=255),
            preserve_default=False,
        ),
        migrations.RunPython(
            populate_and_validate_semantic_aliases,
            migrations.RunPython.noop,
        ),
        migrations.AddIndex(
            model_name="operationalpattern",
            index=models.Index(
                fields=["organization", "normalized_semantic_label"],
                name="pattern_org_sem_label_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="operationalpattern",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "active")),
                fields=("organization", "normalized_semantic_label"),
                name="analytics_pattern_active_sem_label_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="operationalpattern",
            constraint=models.CheckConstraint(
                condition=models.Q(("normalized_semantic_label", ""), _negated=True),
                name="analytics_pattern_norm_sem_label_nonempty",
            ),
        ),
    ]
