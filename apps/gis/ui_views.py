"""
UI Views for Spatial Map Dashboards (Retail & Service Workspaces).
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from apps.workspaces.models import WorkspaceType
from apps.workspaces.services import resolve_authorized_ui_workspace
from apps.retail.models import Branch, Customer, CustomerSegment
from apps.service_ops.models import Employee, ServiceRequest, ServiceCategory, ServiceRequestPriority, ServiceRequestStatus


def _get_workspace(request, expected_type=None):
    return resolve_authorized_ui_workspace(
        request,
        expected_type,
        "gis.view_spatial_layers",
    )


@login_required(login_url="/accounts/login/")
def retail_gis_view(request):
    """
    Renders the Retail GIS Business Analytics Map page (/retail/gis/).
    """
    workspace = _get_workspace(request, WorkspaceType.RETAIL)
    if not workspace:
        return render(request, "retail/no_workspace.html", {"title": "Retail Spatial GIS Analytics"})

    branches = Branch.objects.for_workspace(workspace).filter(is_active=True)
    customer_count = Customer.objects.for_workspace(workspace).filter(is_active=True, location__isnull=False).count()
    branch_count = branches.filter(location__isnull=False).count()

    context = {
        "active_tab": "retail_gis",
        "active_workspace": workspace,
        "branches": branches,
        "customer_count": customer_count,
        "branch_count": branch_count,
        "customer_segments": CustomerSegment.choices,
    }
    return render(request, "retail/gis.html", context)


@login_required(login_url="/accounts/login/")
def service_gis_view(request):
    """
    Renders the Service GIS Operations & Coverage Map page (/services/gis/).
    """
    workspace = _get_workspace(request, WorkspaceType.SERVICE)
    if not workspace:
        return render(request, "retail/no_workspace.html", {"title": "Service GIS Operations Map"})

    technicians = Employee.objects.for_workspace(workspace).filter(is_active=True)
    tickets = ServiceRequest.objects.for_workspace(workspace).filter(location__isnull=False)

    context = {
        "active_tab": "service_gis",
        "active_workspace": workspace,
        "technicians": technicians,
        "technician_count": technicians.filter(current_location__isnull=False).count(),
        "ticket_count": tickets.count(),
        "categories": ServiceCategory.choices,
        "priorities": ServiceRequestPriority.choices,
        "statuses": ServiceRequestStatus.choices,
    }
    return render(request, "service_ops/gis.html", context)
