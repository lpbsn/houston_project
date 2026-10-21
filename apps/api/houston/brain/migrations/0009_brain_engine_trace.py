from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("brain", "0008_brain_decision_corrections"),
    ]

    operations = [
        migrations.AddField(
            model_name="brainanalysis",
            name="trace",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="brainknowledgeversion",
            name="identifier",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.RemoveConstraint(
            model_name="brainknowledgeversion",
            name="brain_know_one_active",
        ),
        migrations.AddConstraint(
            model_name="brainknowledgeversion",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True),
                fields=("identifier",),
                name="brain_know_active_ident_uniq",
            ),
        ),
    ]
