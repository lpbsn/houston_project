from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0002_signalpatternassignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="signalpatternassignment",
            name="assignment_source",
            field=models.CharField(
                choices=[
                    ("classifier", "Classifier"),
                    ("owner_correction", "Owner correction"),
                ],
                default="classifier",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="signalpatternassignment",
            name="owner_correction_signature",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AlterField(
            model_name="patternlifecycleevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("created", "Created"),
                    ("merged", "Merged"),
                    ("renamed", "Renamed"),
                    ("retired", "Retired"),
                    ("signals_moved", "Signals moved"),
                ],
                max_length=64,
            ),
        ),
        migrations.AddIndex(
            model_name="signalpatternassignment",
            index=models.Index(
                fields=["assignment_source"],
                name="sig_pat_assign_source_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="signalpatternassignment",
            constraint=models.CheckConstraint(
                condition=(
                    ~models.Q(("assignment_source", "classifier"))
                    | models.Q(("owner_correction_signature", ""))
                ),
                name="sig_pat_assign_classifier_no_owner",
            ),
        ),
        migrations.AddConstraint(
            model_name="signalpatternassignment",
            constraint=models.CheckConstraint(
                condition=(
                    ~models.Q(("assignment_source", "owner_correction"))
                    | ~models.Q(("owner_correction_signature", ""))
                ),
                name="sig_pat_assign_owner_sig_required",
            ),
        ),
        migrations.AddConstraint(
            model_name="signalpatternassignment",
            constraint=models.CheckConstraint(
                condition=(
                    ~models.Q(("assignment_source", "owner_correction"))
                    | models.Q(("pattern__isnull", False))
                ),
                name="sig_pat_assign_owner_pattern",
            ),
        ),
    ]
