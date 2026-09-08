"""
Data Mapping & Standard Data Model REST API Endpoints.
Adheres strictly to docs/api-conventions.md and workspace tenancy isolation.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied

from apps.workspaces.permissions import IsWorkspaceMember
from apps.accounts.services import has_workspace_permission
from apps.integration.models import DataSource, ImportJob
from apps.mapping.models import (
    MappingProfile,
    MappingRule,
    AIConfirmationStatus,
)
from apps.mapping.canonical import get_canonical_model, CANONICAL_MODELS
from apps.mapping.serializers import (
    MappingProfileSerializer,
    MappingProfileCreateSerializer,
    MappingRuleSerializer,
    MappingRuleCreateSerializer,
    MappingPreviewRequestSerializer,
    MappingApplyRequestSerializer,
    AISuggestRequestSerializer,
)
from apps.mapping.services import (
    create_mapping_profile,
    add_mapping_rule,
    accept_ai_mapping_rule,
    reject_ai_mapping_rule,
    discover_source_fields,
    generate_mapping_preview,
    apply_mapping_to_domain,
)
from apps.mapping.ai_suggester import suggest_mappings_for_fields


def _resolve_workspace(request):
    return getattr(request, "active_workspace", None) or getattr(request._request, "active_workspace", None)


def _require_permission(request, workspace, codename):
    if not has_workspace_permission(request.user, workspace, codename):
        raise PermissionDenied(f"Missing workspace permission: {codename}")


class MappingProfileListCreateAPIView(APIView):
    """
    GET  /api/v1/mapping/profiles/ (List mapping profiles in active workspace)
    POST /api/v1/mapping/profiles/ (Create a new mapping profile)
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request):
        workspace = _resolve_workspace(request)
        if not workspace:
            return Response({"success": False, "error": "No active workspace context."}, status=status.HTTP_400_BAD_REQUEST)

        _require_permission(request, workspace, "mapping.view_mapping")
        target_filter = request.query_params.get("target_entity")
        qs = MappingProfile.objects.for_workspace(workspace).select_related("data_source")
        if target_filter:
            qs = qs.filter(target_entity=target_filter)

        serializer = MappingProfileSerializer(qs, many=True)
        return Response({"success": True, "count": qs.count(), "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        workspace = _resolve_workspace(request)
        if not workspace:
            return Response({"success": False, "error": "No active workspace context."}, status=status.HTTP_400_BAD_REQUEST)

        _require_permission(request, workspace, "mapping.manage_mapping")

        serializer = MappingProfileCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        ds = None
        ds_id = serializer.validated_data.get("data_source_id")
        if ds_id:
            try:
                ds = DataSource.objects.for_workspace(workspace).get(id=ds_id)
            except DataSource.DoesNotExist:
                return Response({"success": False, "error": f"DataSource '{ds_id}' not found in this workspace."}, status=status.HTTP_404_NOT_FOUND)

        try:
            profile = create_mapping_profile(
                workspace=workspace,
                user=request.user,
                name=serializer.validated_data["name"],
                target_entity=serializer.validated_data["target_entity"],
                data_source=ds,
                description=serializer.validated_data.get("description", ""),
            )
            return Response({"success": True, "data": MappingProfileSerializer(profile).data}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MappingProfileDetailAPIView(APIView):
    """
    GET    /api/v1/mapping/profiles/{id}/
    PATCH  /api/v1/mapping/profiles/{id}/
    DELETE /api/v1/mapping/profiles/{id}/
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request, pk):
        workspace = _resolve_workspace(request)
        _require_permission(request, workspace, "mapping.view_mapping")
        profile = get_object_or_404(MappingProfile.objects.for_workspace(workspace).prefetch_related("rules"), id=pk)
        return Response({"success": True, "data": MappingProfileSerializer(profile).data}, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        workspace = _resolve_workspace(request)
        _require_permission(request, workspace, "mapping.manage_mapping")
        profile = get_object_or_404(MappingProfile.objects.for_workspace(workspace), id=pk)

        name = request.data.get("name")
        if name:
            profile.name = name.strip()
        if "description" in request.data:
            profile.description = request.data["description"]
        if "is_active" in request.data:
            profile.is_active = bool(request.data["is_active"])

        profile.save()
        return Response({"success": True, "data": MappingProfileSerializer(profile).data}, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        workspace = _resolve_workspace(request)
        _require_permission(request, workspace, "mapping.manage_mapping")
        profile = get_object_or_404(MappingProfile.objects.for_workspace(workspace), id=pk)

        profile.delete()
        return Response({"success": True, "message": "Mapping profile deleted."}, status=status.HTTP_200_OK)


class MappingProfileFieldsAPIView(APIView):
    """
    GET /api/v1/mapping/profiles/{id}/fields/
    Discovers available source columns from linked data source/import job
    and presents all canonical target fields for the target entity.
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request, pk):
        workspace = _resolve_workspace(request)
        _require_permission(request, workspace, "mapping.view_mapping")
        profile = get_object_or_404(MappingProfile.objects.for_workspace(workspace), id=pk)

        job_id = request.query_params.get("import_job_id")
        import_job = None
        if job_id:
            try:
                import_job = ImportJob.objects.for_workspace(workspace).get(id=job_id)
            except ImportJob.DoesNotExist:
                pass

        discovery = discover_source_fields(import_job=import_job, data_source=profile.data_source)
        model_def = get_canonical_model(profile.target_entity)

        canonical_fields = []
        if model_def:
            for fname, fdef in model_def.fields.items():
                canonical_fields.append({
                    "name": fname,
                    "field_type": fdef.field_type,
                    "required": fdef.required,
                    "description": fdef.description,
                    "choices": fdef.choices,
                    "aliases": fdef.aliases,
                })

        return Response({
            "success": True,
            "profile_id": str(profile.id),
            "target_entity": profile.target_entity,
            "source_discovery": discovery,
            "canonical_fields": canonical_fields,
        }, status=status.HTTP_200_OK)


class MappingProfileRulesAPIView(APIView):
    """
    POST /api/v1/mapping/profiles/{id}/rules/
    Adds a new mapping rule to the profile.
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def post(self, request, pk):
        workspace = _resolve_workspace(request)
        _require_permission(request, workspace, "mapping.manage_mapping")
        profile = get_object_or_404(MappingProfile.objects.for_workspace(workspace), id=pk)

        serializer = MappingRuleCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        rule = add_mapping_rule(
            profile=profile,
            user=request.user,
            source_field=serializer.validated_data["source_field"],
            target_field=serializer.validated_data["target_field"],
            rule_type=serializer.validated_data.get("rule_type", "FIELD_MAPPING"),
            transformation_config=serializer.validated_data.get("transformation_config", {}),
            confidence_score=serializer.validated_data.get("confidence_score", 1.0),
            ai_status=serializer.validated_data.get("ai_status", AIConfirmationStatus.ACCEPTED),
            order=serializer.validated_data.get("order", 0),
        )

        return Response({"success": True, "data": MappingRuleSerializer(rule).data}, status=status.HTTP_201_CREATED)


class MappingRuleDetailAPIView(APIView):
    """
    PATCH  /api/v1/mapping/profiles/{id}/rules/{rule_id}/ (Update rule or Accept/Reject AI rule)
    DELETE /api/v1/mapping/profiles/{id}/rules/{rule_id}/ (Delete rule)
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def patch(self, request, pk, rule_id):
        workspace = _resolve_workspace(request)
        _require_permission(request, workspace, "mapping.manage_mapping")
        profile = get_object_or_404(MappingProfile.objects.for_workspace(workspace), id=pk)
        rule = get_object_or_404(profile.rules.all(), id=rule_id)

        action = request.data.get("action")
        if action == "ACCEPT_AI":
            rule = accept_ai_mapping_rule(rule, request.user)
            return Response({"success": True, "data": MappingRuleSerializer(rule).data}, status=status.HTTP_200_OK)
        elif action == "REJECT_AI":
            rule = reject_ai_mapping_rule(rule, request.user)
            return Response({"success": True, "data": MappingRuleSerializer(rule).data}, status=status.HTTP_200_OK)

        serializer = MappingRuleCreateSerializer(rule, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({"success": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response({"success": True, "data": MappingRuleSerializer(rule).data}, status=status.HTTP_200_OK)

    def delete(self, request, pk, rule_id):
        workspace = _resolve_workspace(request)
        _require_permission(request, workspace, "mapping.manage_mapping")
        profile = get_object_or_404(MappingProfile.objects.for_workspace(workspace), id=pk)
        rule = get_object_or_404(profile.rules.all(), id=rule_id)

        rule.delete()
        return Response({"success": True, "message": "Mapping rule removed."}, status=status.HTTP_200_OK)


class MappingPreviewAPIView(APIView):
    """
    POST /api/v1/mapping/preview/
    Read-only simulation preview. Transforms records and validates without database writes.
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def post(self, request):
        workspace = _resolve_workspace(request)
        if not workspace:
            return Response({"success": False, "error": "No active workspace context."}, status=status.HTTP_400_BAD_REQUEST)

        _require_permission(request, workspace, "mapping.view_mapping")
        serializer = MappingPreviewRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        profile = get_object_or_404(
            MappingProfile.objects.for_workspace(workspace),
            id=serializer.validated_data["profile_id"],
        )

        import_job = None
        job_id = serializer.validated_data.get("import_job_id")
        if job_id:
            import_job = get_object_or_404(ImportJob.objects.for_workspace(workspace), id=job_id)

        raw_records = serializer.validated_data.get("raw_records")
        sample_count = serializer.validated_data.get("sample_count", 5)

        preview_data = generate_mapping_preview(
            workspace=workspace,
            profile=profile,
            import_job=import_job,
            raw_records_data=raw_records,
            sample_count=sample_count,
        )

        return Response({"success": True, "data": preview_data}, status=status.HTTP_200_OK)


class MappingApplyAPIView(APIView):
    """
    POST /api/v1/mapping/apply/
    Atomically applies mapping rules from profile to staged ImportJob records
    and commits canonical records into domain tables.
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def post(self, request):
        workspace = _resolve_workspace(request)
        if not workspace:
            return Response({"success": False, "error": "No active workspace context."}, status=status.HTTP_400_BAD_REQUEST)

        _require_permission(request, workspace, "mapping.apply_mapping")

        serializer = MappingApplyRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        profile = get_object_or_404(
            MappingProfile.objects.for_workspace(workspace),
            id=serializer.validated_data["profile_id"],
        )
        import_job = get_object_or_404(
            ImportJob.objects.for_workspace(workspace),
            id=serializer.validated_data["import_job_id"],
        )
        strict = serializer.validated_data.get("strict", False)

        result = apply_mapping_to_domain(
            workspace=workspace,
            user=request.user,
            profile=profile,
            import_job=import_job,
            strict=strict,
        )

        http_status = status.HTTP_200_OK if result["status"] in ("COMPLETED", "PARTIAL") else status.HTTP_400_BAD_REQUEST
        return Response({"success": result["status"] != "FAILED", "data": result}, status=http_status)


class MappingAISuggestAPIView(APIView):
    """
    POST /api/v1/mapping/ai-suggest/
    Recommendation mode ONLY: analyzes source columns and data samples to suggest mapping rules
    with confidence scores and explanatory reasons.
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def post(self, request):
        workspace = _resolve_workspace(request)
        if not workspace:
            return Response({"success": False, "error": "No active workspace context."}, status=status.HTTP_400_BAD_REQUEST)

        _require_permission(request, workspace, "mapping.view_mapping")
        serializer = AISuggestRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        target_entity = serializer.validated_data["target_entity"]
        source_columns = serializer.validated_data["source_columns"]
        sample_values = serializer.validated_data.get("sample_values", {})
        inferred_types = serializer.validated_data.get("inferred_types", {})

        suggestions = suggest_mappings_for_fields(
            source_columns=source_columns,
            target_entity=target_entity,
            sample_values=sample_values,
            inferred_types=inferred_types,
        )

        return Response({
            "success": True,
            "target_entity": target_entity,
            "total_suggestions": len(suggestions),
            "suggestions": suggestions,
            "notice": "AI suggestions are advisory. Human review and acceptance are required before rules become active.",
        }, status=status.HTTP_200_OK)
