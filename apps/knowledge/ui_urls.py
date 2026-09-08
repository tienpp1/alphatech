from django.urls import path

from apps.knowledge.ui_views import ai_assistant_ui_view, knowledge_base_ui_view

urlpatterns = [
    path("ai/", ai_assistant_ui_view, name="noibo_ai_assistant"),
    path("knowledge/", knowledge_base_ui_view, name="noibo_knowledge_base"),
]
