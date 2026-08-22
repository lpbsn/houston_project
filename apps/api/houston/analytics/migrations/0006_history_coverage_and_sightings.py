import django.db.models.deletion
import uuid
from django.db import migrations, models
from django.db.migrations.exceptions import IrreversibleError
from django.utils import timezone

# Frozen snapshot of the Analytics history cutover. Do not edit after merge.
# Runtime re-runs and tests use houston.analytics.cutover.


def _quoted_table(apps, schema_editor, app_label, model_name):
    model = apps.get_model(app_label, model_name)
    return schema_editor.connection.ops.quote_name(model._meta.db_table)


def _require_postgresql(schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("Analytics history cutover requires PostgreSQL.")


def apply_history_cutover(apps, schema_editor):
    _require_postgresql(schema_editor)
    Coverage = apps.get_model("analytics", "AnalyticsHistoryCoverage")
    coverage, _created = Coverage.objects.using(schema_editor.connection.alias).get_or_create(
        singleton_key=1,
        defaults={"reliable_from": timezone.now()},
    )
    reliable_from = coverage.reliable_from

    signals = _quoted_table(apps, schema_editor, "signals", "Signal")
    signal_events = _quoted_table(apps, schema_editor, "signals", "SignalLifecycleEvent")
    executions = _quoted_table(apps, schema_editor, "action_plans", "ActionPlanExecution")
    execution_events = _quoted_table(
        apps, schema_editor, "action_plans", "ActionPlanExecutionLifecycleEvent"
    )
    end_at_exec = (
        "CASE WHEN e.end_at IS NULL THEN NULL "
        "ELSE to_char(e.end_at AT TIME ZONE 'UTC', "
        """'YYYY-MM-DD"T"HH24:MI:SS.US') || '+00:00' END"""
    )
    statements = [
        (
            f"""
            INSERT INTO {signal_events} (
                id, created_at, updated_at, signal_id, establishment_id,
                event_type, actor_membership_id, occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                s.id,
                s.establishment_id,
                'signal.history_baseline',
                NULL,
                %s,
                jsonb_build_object('to_status', s.status)
            FROM {signals} s
            WHERE NOT EXISTS (
                SELECT 1
                FROM {signal_events} existing
                WHERE existing.signal_id = s.id
                  AND existing.event_type = 'signal.history_baseline'
            )
            """,
            [reliable_from],
        ),
        (
            f"""
            INSERT INTO {execution_events} (
                id, created_at, updated_at, action_plan_execution_id,
                establishment_id, event_type, actor_membership_id,
                occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                e.id,
                e.establishment_id,
                'action_plan_execution.history_baseline',
                NULL,
                %s,
                jsonb_build_object(
                    'to_status', e.status,
                    'end_at', {end_at_exec}
                )
            FROM {executions} e
            WHERE NOT EXISTS (
                SELECT 1
                FROM {execution_events} existing
                WHERE existing.action_plan_execution_id = e.id
                  AND existing.event_type = 'action_plan_execution.history_baseline'
            )
            """,
            [reliable_from],
        ),
        (
            f"""
            INSERT INTO {signal_events} (
                id, created_at, updated_at, signal_id, establishment_id,
                event_type, actor_membership_id, occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                s.id,
                s.establishment_id,
                'signal.resolved',
                NULL,
                s.resolved_at,
                jsonb_build_object('to_status', 'resolved')
            FROM {signals} s
            WHERE s.status = 'resolved'
              AND s.resolved_at IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM {signal_events} existing
                WHERE existing.signal_id = s.id
                  AND existing.event_type = 'signal.resolved'
                  AND existing.occurred_at = s.resolved_at
              )
            """,
            [],
        ),
        (
            f"""
            INSERT INTO {signal_events} (
                id, created_at, updated_at, signal_id, establishment_id,
                event_type, actor_membership_id, occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                s.id,
                s.establishment_id,
                'signal.canceled',
                NULL,
                s.canceled_at,
                jsonb_build_object('to_status', 'canceled')
            FROM {signals} s
            WHERE s.status = 'canceled'
              AND s.canceled_at IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM {signal_events} existing
                WHERE existing.signal_id = s.id
                  AND existing.event_type = 'signal.canceled'
                  AND existing.occurred_at = s.canceled_at
              )
            """,
            [],
        ),
        (
            f"""
            INSERT INTO {signal_events} (
                id, created_at, updated_at, signal_id, establishment_id,
                event_type, actor_membership_id, occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                s.id,
                s.establishment_id,
                'signal.archived',
                NULL,
                s.archived_at,
                jsonb_build_object('to_status', 'archived')
            FROM {signals} s
            WHERE s.status = 'archived'
              AND s.archived_at IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM {signal_events} existing
                WHERE existing.signal_id = s.id
                  AND existing.event_type = 'signal.archived'
                  AND existing.occurred_at = s.archived_at
              )
            """,
            [],
        ),
        (
            f"""
            INSERT INTO {execution_events} (
                id, created_at, updated_at, action_plan_execution_id,
                establishment_id, event_type, actor_membership_id,
                occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                e.id,
                e.establishment_id,
                'action_plan_execution.marked_done',
                NULL,
                e.marked_done_at,
                jsonb_build_object(
                    'to_status', 'pending_validation',
                    'end_at', {end_at_exec}
                )
            FROM {executions} e
            WHERE e.status = 'pending_validation'
              AND e.marked_done_at IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM {execution_events} existing
                WHERE existing.action_plan_execution_id = e.id
                  AND existing.event_type = 'action_plan_execution.marked_done'
                  AND existing.occurred_at = e.marked_done_at
              )
            """,
            [],
        ),
        (
            f"""
            INSERT INTO {execution_events} (
                id, created_at, updated_at, action_plan_execution_id,
                establishment_id, event_type, actor_membership_id,
                occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                e.id,
                e.establishment_id,
                'action_plan_execution.marked_done',
                NULL,
                e.marked_done_at,
                jsonb_build_object(
                    'to_status', CASE
                        WHEN e.validated_at IS NOT NULL THEN 'pending_validation'
                        ELSE 'done'
                    END,
                    'end_at', {end_at_exec}
                )
            FROM {executions} e
            WHERE e.status = 'done'
              AND e.marked_done_at IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM {execution_events} existing
                WHERE existing.action_plan_execution_id = e.id
                  AND existing.event_type = 'action_plan_execution.marked_done'
                  AND existing.occurred_at = e.marked_done_at
              )
            """,
            [],
        ),
        (
            f"""
            INSERT INTO {execution_events} (
                id, created_at, updated_at, action_plan_execution_id,
                establishment_id, event_type, actor_membership_id,
                occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                e.id,
                e.establishment_id,
                'action_plan_execution.validated',
                NULL,
                e.validated_at,
                jsonb_build_object(
                    'to_status', 'done',
                    'end_at', {end_at_exec}
                )
            FROM {executions} e
            WHERE e.status = 'done'
              AND e.marked_done_at IS NOT NULL
              AND e.validated_at IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM {execution_events} existing
                WHERE existing.action_plan_execution_id = e.id
                  AND existing.event_type = 'action_plan_execution.validated'
                  AND existing.occurred_at = e.validated_at
              )
            """,
            [],
        ),
        (
            f"""
            INSERT INTO {execution_events} (
                id, created_at, updated_at, action_plan_execution_id,
                establishment_id, event_type, actor_membership_id,
                occurred_at, metadata_safe
            )
            SELECT
                gen_random_uuid(),
                now(),
                now(),
                e.id,
                e.establishment_id,
                'action_plan_execution.canceled',
                NULL,
                e.canceled_at,
                jsonb_build_object(
                    'to_status', 'canceled',
                    'end_at', {end_at_exec}
                )
            FROM {executions} e
            WHERE e.status = 'canceled'
              AND e.canceled_at IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM {execution_events} existing
                WHERE existing.action_plan_execution_id = e.id
                  AND existing.event_type = 'action_plan_execution.canceled'
                  AND existing.occurred_at = e.canceled_at
              )
            """,
            [],
        ),
    ]
    with schema_editor.connection.cursor() as cursor:
        for sql, params in statements:
            cursor.execute(sql, params)


def refuse_history_cutover_reverse(apps, schema_editor):
    raise IrreversibleError(
        "analytics.0006 is an irreversible history frontier. Reversing it "
        "would drop AnalyticsHistoryCoverage.reliable_from while leaving "
        "lifecycle baselines and terminal events in signals and action_plans."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("action_plans", "0014_execution_history_baseline_and_deadline"),
        ("analytics", "0005_pattern_semantic_alias"),
        ("establishments", "0030_seed_onboarding_drafts"),
        ("signals", "0017_signal_created_and_history_baseline"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnalyticsHistoryCoverage",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("singleton_key", models.PositiveSmallIntegerField(default=1, editable=False)),
                ("reliable_from", models.DateTimeField()),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("singleton_key",),
                        name="analytics_history_coverage_singleton",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("singleton_key", 1)),
                        name="analytics_history_coverage_key_one",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="PatternEstablishmentSighting",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("observed_at", models.DateTimeField()),
                (
                    "establishment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pattern_sightings",
                        to="establishments.establishment",
                    ),
                ),
                (
                    "pattern",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="establishment_sightings",
                        to="analytics.operationalpattern",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["establishment", "observed_at"],
                        name="analytics_sighting_est_at_idx",
                    ),
                    models.Index(
                        fields=["pattern", "observed_at"],
                        name="analytics_sighting_pat_at_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("pattern", "establishment"),
                        name="analytics_pattern_est_sighting_uniq",
                    ),
                ],
            },
        ),
        migrations.RunPython(apply_history_cutover, refuse_history_cutover_reverse),
    ]
