import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="SocialIdentity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[("GOOGLE", "Google")], max_length=20)),
                ("subject", models.CharField(max_length=255)),
                ("provider_email", models.EmailField(max_length=254)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="social_identities", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "public_web_social_identity"},
        ),
        migrations.CreateModel(
            name="CustomerEmailDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event_type", models.CharField(choices=[("WELCOME", "Welcome"), ("LOGIN_ALERT", "Login alert"), ("ORDER", "Order"), ("SERVICE_REQUEST", "Service request"), ("CONTACT", "Contact")], max_length=30)),
                ("entity_type", models.CharField(blank=True, max_length=50)),
                ("entity_id", models.CharField(blank=True, max_length=100)),
                ("recipient", models.EmailField(max_length=254)),
                ("subject", models.CharField(max_length=255)),
                ("plain_body", models.TextField()),
                ("html_body", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("SENT", "Sent"), ("FAILED", "Failed")], default="PENDING", max_length=10)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("last_error_code", models.CharField(blank=True, max_length=80)),
                ("attempted_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("deduplication_key", models.CharField(max_length=255, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="customer_email_deliveries", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "public_web_customer_email_delivery", "ordering": ("-created_at",)},
        ),
        migrations.AddConstraint(
            model_name="socialidentity",
            constraint=models.UniqueConstraint(fields=("provider", "subject"), name="uniq_social_provider_subject"),
        ),
        migrations.AddConstraint(
            model_name="socialidentity",
            constraint=models.UniqueConstraint(fields=("provider", "user"), name="uniq_social_provider_user"),
        ),
        migrations.AddIndex(
            model_name="customeremaildelivery",
            index=models.Index(fields=["status", "created_at"], name="public_email_status_idx"),
        ),
    ]
