from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("approvals", "0001_initial"),
        ("recommendations", "0002_alter_recommendation_recommendation_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="recommendation",
            name="approval_request",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_recommendation",
                to="approvals.approvalrequest",
            ),
        ),
        migrations.AddField(
            model_name="recommendation",
            name="proposed_action",
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddField(
            model_name="recommendation",
            name="proposed_parameters",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
