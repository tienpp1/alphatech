"""
Serializers for GIS endpoints & Spatial Responses.
"""

from rest_framework import serializers


class NearbyTechnicianCandidateSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    code = serializers.CharField()
    full_name = serializers.CharField()
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_null=True)
    skills = serializers.ListField(child=serializers.CharField(), required=False)
    hourly_labor_rate = serializers.FloatField()
    formatted_rate = serializers.CharField()
    current_workload_score = serializers.FloatField()
    is_available = serializers.BooleanField()
    distance_meters = serializers.FloatField()
    distance_km = serializers.FloatField()
    coordinates = serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2)


class NearbyTechniciansResponseSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField()
    request_number = serializers.CharField()
    ticket_title = serializers.CharField()
    ticket_coordinates = serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2)
    search_radius_km = serializers.FloatField()
    available_only = serializers.BooleanField()
    required_skill = serializers.CharField(required=False, allow_null=True)
    total_candidates = serializers.IntegerField()
    candidates = NearbyTechnicianCandidateSerializer(many=True)


class BranchSpatialRevenueItemSerializer(serializers.Serializer):
    branch_id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()
    region = serializers.CharField()
    coordinates = serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2, allow_null=True)
    revenue = serializers.FloatField()
    order_count = serializers.IntegerField()
    revenue_share_pct = serializers.FloatField()


class RetailSpatialRevenueAnalyticsSerializer(serializers.Serializer):
    workspace_id = serializers.CharField()
    total_revenue = serializers.FloatField()
    total_orders = serializers.IntegerField()
    branch_count = serializers.IntegerField()
    branch_rankings = BranchSpatialRevenueItemSerializer(many=True)
