from django.contrib import admin
from apps.recommendations.models import Recommendation


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ["id", "workspace", "recommendation_type", "priority", "status", "created_at"]
    list_filter = ["workspace", "recommendation_type", "priority", "status"]
    search_fields = ["title", "workspace__code"]
