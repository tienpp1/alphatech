from django.db import migrations
from django.db.models import F, Q


def repair_customer_workspace_integrity(apps, schema_editor):
    Customer = apps.get_model("retail", "Customer")
    ServiceRequest = apps.get_model("service_ops", "ServiceRequest")

    mismatched = ServiceRequest.objects.exclude(
        workspace_id=F("customer__workspace_id")
    ).select_related("customer")

    relinked = {}
    for service_request in mismatched.iterator():
        source = service_request.customer
        cache_key = (source.pk, service_request.workspace_id)
        target = relinked.get(cache_key)
        if target is None:
            identity_filter = Q()
            if source.email:
                identity_filter |= Q(email__iexact=source.email)
            if source.phone:
                identity_filter |= Q(phone=source.phone)
            target = (
                Customer.objects.filter(identity_filter, workspace_id=service_request.workspace_id).first()
                if identity_filter
                else None
            )
            if target is None:
                base_code = f"CUST-MIG-{source.pk}"
                code = base_code
                suffix = 1
                while Customer.objects.filter(workspace_id=service_request.workspace_id, code=code).exists():
                    suffix += 1
                    code = f"{base_code}-{suffix}"
                target = Customer.objects.create(
                    workspace_id=service_request.workspace_id,
                    code=code,
                    name=source.name,
                    email=source.email,
                    phone=source.phone,
                    address=source.address,
                    location=source.location,
                    latitude=source.latitude,
                    longitude=source.longitude,
                    customer_segment=source.customer_segment,
                    is_active=source.is_active,
                )
            relinked[cache_key] = target

        ServiceRequest.objects.filter(pk=service_request.pk).update(customer_id=target.pk)


class Migration(migrations.Migration):
    dependencies = [
        ("service_ops", "0002_employee_hourly_labor_rate_service_category_and_more"),
        ("retail", "0004_remove_product_unique_workspace_product_sku_and_more"),
    ]

    operations = [
        migrations.RunPython(repair_customer_workspace_integrity, migrations.RunPython.noop),
    ]
