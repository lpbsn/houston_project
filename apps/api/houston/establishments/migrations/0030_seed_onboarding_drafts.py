from django.db import migrations


ONBOARDING_NON_TERMINAL_STATUSES = (
    "started",
    "description_submitted",
    "configuring_runtime",
    "proposal_ready",
    "validating_sections",
    "ready_for_activation",
)


def empty_onboarding_draft_payload():
    return {
        "current_step": "structure",
        "establishment": {"name": "", "description": ""},
        "business_units": [],
        "activity_subjects": [],
        "team": {"director": None, "members": []},
    }


def seed_eligible_onboarding_drafts(apps, schema_editor):
    OnboardingSession = apps.get_model("establishments", "OnboardingSession")
    OnboardingDraft = apps.get_model("establishments", "OnboardingDraft")
    BusinessUnit = apps.get_model("establishments", "BusinessUnit")

    establishment_ids_with_bu = BusinessUnit.objects.values_list(
        "establishment_id",
        flat=True,
    )
    eligible_sessions = (
        OnboardingSession.objects.filter(
            status__in=ONBOARDING_NON_TERMINAL_STATUSES,
            establishment__status="draft",
        )
        .exclude(establishment_id__in=establishment_ids_with_bu)
        .filter(draft__isnull=True)
    )

    drafts = [
        OnboardingDraft(
            onboarding_session_id=session.id,
            payload=empty_onboarding_draft_payload(),
        )
        for session in eligible_sessions.iterator()
    ]
    if drafts:
        OnboardingDraft.objects.bulk_create(drafts, batch_size=500)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0029_onboardingdraft"),
    ]

    operations = [
        migrations.RunPython(seed_eligible_onboarding_drafts, noop_reverse),
    ]
