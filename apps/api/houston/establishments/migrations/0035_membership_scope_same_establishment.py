from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0034_remove_establishmentmembership_notifications_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="membershipscope",
            name="establishment",
            field=models.ForeignKey(
                db_index=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="membership_scopes",
                to="establishments.establishment",
            ),
        ),
        migrations.AddConstraint(
            model_name="establishmentmembership",
            constraint=models.UniqueConstraint(
                fields=("id", "establishment"),
                name="membership_id_establishment_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="businessunit",
            constraint=models.UniqueConstraint(
                fields=("id", "establishment"),
                name="bu_id_establishment_uniq",
            ),
        ),
        migrations.RunSQL(
            sql="""
            UPDATE establishments_membershipscope AS scope
            SET establishment_id = membership.establishment_id
            FROM establishments_establishmentmembership AS membership
            WHERE scope.membership_id = membership.id;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name="membershipscope",
            name="establishment",
            field=models.ForeignKey(
                db_index=False,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="membership_scopes",
                to="establishments.establishment",
            ),
        ),
        migrations.RunSQL(
            sql="""
            ALTER TABLE establishments_membershipscope
            ADD CONSTRAINT membershipscope_membership_est_fk
            FOREIGN KEY (membership_id, establishment_id)
            REFERENCES establishments_establishmentmembership (id, establishment_id);
            ALTER TABLE establishments_membershipscope
            ADD CONSTRAINT membershipscope_bu_est_fk
            FOREIGN KEY (business_unit_id, establishment_id)
            REFERENCES establishments_businessunit (id, establishment_id);
            """,
            reverse_sql="""
            ALTER TABLE establishments_membershipscope
            DROP CONSTRAINT IF EXISTS membershipscope_membership_est_fk;
            ALTER TABLE establishments_membershipscope
            DROP CONSTRAINT IF EXISTS membershipscope_bu_est_fk;
            """,
        ),
    ]
