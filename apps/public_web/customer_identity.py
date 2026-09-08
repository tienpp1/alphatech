"""Account ownership is explicit; submitted email/phone never proves ownership."""
import uuid

from apps.retail.models import Customer, Order
from apps.workspaces.models import WorkspaceType


def customer_for_submission(*, workspace, user, name, email="", phone="", address=""):
    defaults = dict(code=f"CUST-PUB-{uuid.uuid4().hex[:20]}", name=name,
                    email=email, phone=phone, address=address)
    if user is not None and user.is_authenticated:
        defaults["email"] = user.email.strip().lower()
        return Customer.objects.get_or_create(workspace=workspace, user=user, defaults=defaults)[0]
    # A guest cannot attach a submission to somebody else's customer record.
    return Customer.objects.create(workspace=workspace, **defaults)


def customer_orders(user):
    # created_by also supports authenticated orders predating the explicit relation.
    # Customer metadata may be edited; it must not transfer historical ownership.
    return Order.objects.filter(workspace__workspace_type=WorkspaceType.RETAIL, created_by=user)
