from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("retail", "0007_order_fulfillment_reservation")]

    operations = [
        migrations.CreateModel(
            name="ProductImageContent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.BinaryField()),
                ("image", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                                               related_name="durable_content", to="retail.productimage")),
            ],
        ),
    ]
