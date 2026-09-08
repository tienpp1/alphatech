from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("public_web", "0001_customer_email_and_social_identity")]

    operations = [
        migrations.AlterField(
            model_name="customeremaildelivery",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("EMAIL_VERIFICATION", "Email verification"),
                    ("WELCOME", "Welcome"),
                    ("LOGIN_ALERT", "Login alert"),
                    ("ORDER", "Order"),
                    ("SERVICE_REQUEST", "Service request"),
                    ("CONTACT", "Contact"),
                ],
                max_length=30,
            ),
        ),
    ]
