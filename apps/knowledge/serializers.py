"""
DRF Serializers for Knowledge Base, Documents, Chunks, and AI Chat.
"""

from rest_framework import serializers
from apps.knowledge.models import (
    KnowledgeBase,
    Document,
    DocumentChunk,
    ConversationSession,
    ChatMessage,
)


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    document_count = serializers.IntegerField(source="documents.count", read_only=True)

    class Meta:
        model = KnowledgeBase
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "document_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "document_count"]


class DocumentChunkSerializer(serializers.ModelSerializer):
    has_vector = serializers.SerializerMethodField()

    class Meta:
        model = DocumentChunk
        fields = [
            "id",
            "chunk_index",
            "content",
            "token_count",
            "metadata",
            "has_vector",
            "created_at",
        ]
        read_only_fields = ["id", "chunk_index", "content", "token_count", "metadata", "has_vector", "created_at"]

    def get_has_vector(self, obj) -> bool:
        return bool(obj.embedding)


class DocumentSerializer(serializers.ModelSerializer):
    knowledge_base_name = serializers.CharField(source="knowledge_base.name", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "knowledge_base",
            "knowledge_base_name",
            "title",
            "file",
            "file_type",
            "file_size",
            "status",
            "chunk_count",
            "error_message",
            "source_metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "file_size",
            "status",
            "chunk_count",
            "error_message",
            "source_metadata",
            "created_at",
            "updated_at",
            "knowledge_base_name",
        ]


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "role",
            "content",
            "sources",
            "tools_used",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ConversationSessionSerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(source="messages.count", read_only=True)

    class Meta:
        model = ConversationSession
        fields = [
            "id",
            "title",
            "message_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "message_count", "created_at", "updated_at"]


class ChatQueryRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False, max_length=4000)
    session_id = serializers.IntegerField(required=False, allow_null=True)
