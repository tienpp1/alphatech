"""
URL routing for Knowledge Base, Document Ingestion, and AI Assistant REST APIs and Web UI.
"""

from django.urls import path
from apps.knowledge.views import (
    KnowledgeBaseListCreateAPIView,
    KnowledgeBaseDetailAPIView,
    DocumentListCreateAPIView,
    DocumentDetailAPIView,
    DocumentReindexAPIView,
    DocumentChunkListAPIView,
    ConversationSessionListAPIView,
    ConversationSessionDetailAPIView,
    AIChatAPIView,
)
from apps.knowledge.ui_views import ai_assistant_ui_view, knowledge_base_ui_view

urlpatterns = [
    # REST API endpoints
    path("api/v1/ai/chat/", AIChatAPIView.as_view(), name="api_ai_chat"),
    path("api/v1/ai/sessions/", ConversationSessionListAPIView.as_view(), name="api_ai_sessions"),
    path("api/v1/ai/sessions/<int:pk>/messages/", ConversationSessionDetailAPIView.as_view(), name="api_ai_session_messages"),
    path("api/v1/knowledge/bases/", KnowledgeBaseListCreateAPIView.as_view(), name="api_knowledge_bases"),
    path("api/v1/knowledge/bases/<int:pk>/", KnowledgeBaseDetailAPIView.as_view(), name="api_knowledge_base_detail"),
    path("api/v1/knowledge/documents/", DocumentListCreateAPIView.as_view(), name="api_knowledge_documents"),
    path("api/v1/knowledge/documents/<int:pk>/", DocumentDetailAPIView.as_view(), name="api_knowledge_document_detail"),
    path("api/v1/knowledge/documents/<int:pk>/reindex/", DocumentReindexAPIView.as_view(), name="api_knowledge_document_reindex"),
    path("api/v1/knowledge/documents/<int:pk>/chunks/", DocumentChunkListAPIView.as_view(), name="api_knowledge_document_chunks"),

    # Web UI endpoints
    path("ai/", ai_assistant_ui_view, name="ai_assistant_ui"),
    path("knowledge/", knowledge_base_ui_view, name="knowledge_base_ui"),
]
