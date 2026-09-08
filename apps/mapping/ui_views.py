"""
Web UI Views for Data Mapping Engine & Mapping Studio.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from apps.workspaces.services import resolve_authorized_ui_workspace
from apps.accounts.services import has_workspace_permission
from apps.integration.models import DataSource, ImportJob
from apps.mapping.models import MappingProfile, MappingRule, RuleType, AIConfirmationStatus
from apps.mapping.canonical import CANONICAL_MODELS, get_canonical_model
from apps.mapping.services import (
    discover_source_fields,
    create_mapping_profile,
    add_mapping_rule,
    generate_mapping_preview,
    apply_mapping_to_domain,
)


@login_required
def mapping_dashboard_view(request):
    """
    Renders the Mapping Profiles Management Dashboard (/mapping/).
    """
    workspace = resolve_authorized_ui_workspace(request, None, "mapping.view_mapping")
    membership = getattr(request, "active_membership", None)

    profiles = MappingProfile.objects.for_workspace(workspace).select_related("data_source").prefetch_related("rules")
    total_profiles = profiles.count()
    active_rules_total = sum(p.active_rules_count for p in profiles)

    # Domain summary
    retail_profiles = profiles.filter(target_entity__in=["Customer", "Product", "Order", "OrderItem", "Branch"]).count()
    service_profiles = profiles.filter(target_entity__in=["Service", "Employee", "ServiceRequest", "Task", "LaborEntry"]).count()

    context = {
        "workspace": workspace,
        "membership": membership,
        "profiles": profiles,
        "total_profiles": total_profiles,
        "active_rules_total": active_rules_total,
        "retail_profiles": retail_profiles,
        "service_profiles": service_profiles,
        "can_manage": request.user.is_superuser or has_workspace_permission(request.user, workspace, "mapping.manage_mapping"),
        "can_apply": request.user.is_superuser or has_workspace_permission(request.user, workspace, "mapping.apply_mapping"),
    }
    return render(request, "mapping/dashboard.html", context)


@login_required
def mapping_profile_create_view(request):
    """
    Renders the Profile Creation Wizard (/mapping/profiles/new/).
    """
    workspace = resolve_authorized_ui_workspace(request, None, "mapping.manage_mapping")
    membership = getattr(request, "active_membership", None)

    if request.method == "POST":
        if not has_workspace_permission(request.user, workspace, "mapping.manage_mapping"):
            raise PermissionDenied("Missing workspace permission: mapping.manage_mapping")
        name = request.POST.get("name")
        target_entity = request.POST.get("target_entity")
        ds_id = request.POST.get("data_source_id")
        description = request.POST.get("description", "")

        ds = None
        if ds_id:
            ds = DataSource.objects.for_workspace(workspace).filter(id=ds_id).first()

        try:
            profile = create_mapping_profile(
                workspace=workspace,
                user=request.user,
                name=name,
                target_entity=target_entity,
                data_source=ds,
                description=description,
            )
            messages.success(request, f"Mapping profile '{profile.name}' created successfully.")
            return redirect("mapping_studio", pk=profile.id)
        except Exception as e:
            messages.error(request, f"Error creating profile: {str(e)}")

    data_sources = DataSource.objects.for_workspace(workspace).filter(is_active=True)
    canonical_entities = [
        {"name": k, "display_name": v.display_name, "domain": v.domain, "description": v.description}
        for k, v in CANONICAL_MODELS.items()
    ]

    context = {
        "workspace": workspace,
        "data_sources": data_sources,
        "canonical_entities": canonical_entities,
    }
    return render(request, "mapping/profile_form.html", context)


@login_required
def mapping_studio_view(request, pk):
    """
    Renders the Interactive Mapping Studio (/mapping/profiles/<uuid:pk>/).
    Features source column discovery, rule builder, AI suggestion actions, and live transform preview.
    """
    workspace = resolve_authorized_ui_workspace(request, None, "mapping.view_mapping")
    membership = getattr(request, "active_membership", None)

    profile = get_object_or_404(MappingProfile.objects.for_workspace(workspace).prefetch_related("rules"), id=pk)

    # Handle Rule creation via Studio Form POST
    if request.method == "POST" and "action" in request.POST:
        if not has_workspace_permission(request.user, workspace, "mapping.manage_mapping"):
            raise PermissionDenied("Missing workspace permission: mapping.manage_mapping")
        action = request.POST.get("action")
        if action == "ADD_RULE":
            source_field = request.POST.get("source_field")
            target_field = request.POST.get("target_field")
            rule_type = request.POST.get("rule_type", "FIELD_MAPPING")
            add_mapping_rule(
                profile=profile,
                user=request.user,
                source_field=source_field,
                target_field=target_field,
                rule_type=rule_type,
            )
            messages.success(request, f"Rule '{source_field} -> {target_field}' added.")
            return redirect("mapping_studio", pk=profile.id)

        elif action == "DELETE_RULE":
            rule_id = request.POST.get("rule_id")
            rule = profile.rules.filter(id=rule_id).first()
            if rule:
                rule.delete()
                messages.success(request, "Rule deleted.")
            return redirect("mapping_studio", pk=profile.id)

        elif action == "ACCEPT_AI":
            rule_id = request.POST.get("rule_id")
            rule = profile.rules.filter(id=rule_id).first()
            if rule:
                rule.ai_status = AIConfirmationStatus.ACCEPTED
                rule.is_active = True
                rule.save()
                messages.success(request, f"AI Rule '{rule.target_field}' accepted and activated.")
            return redirect("mapping_studio", pk=profile.id)

    # Field Discovery
    selected_job_id = request.GET.get("job_id")
    import_job = None
    if selected_job_id:
        import_job = ImportJob.objects.for_workspace(workspace).filter(id=selected_job_id).first()

    discovery = discover_source_fields(import_job=import_job, data_source=profile.data_source)
    model_def = get_canonical_model(profile.target_entity)

    # Available jobs for preview / testing
    jobs = ImportJob.objects.for_workspace(workspace).order_by("-created_at")[:15]

    context = {
        "workspace": workspace,
        "membership": membership,
        "profile": profile,
        "rules": profile.rules.all().order_by("order", "id"),
        "model_def": model_def,
        "discovery": discovery,
        "import_jobs": jobs,
        "selected_job": import_job,
        "rule_types": RuleType.choices,
        "can_manage": request.user.is_superuser or has_workspace_permission(request.user, workspace, "mapping.manage_mapping"),
        "can_apply": request.user.is_superuser or has_workspace_permission(request.user, workspace, "mapping.apply_mapping"),
    }
    return render(request, "mapping/mapping_studio.html", context)
