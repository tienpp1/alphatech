import os
from django.conf import settings
from django.db import models
from apps.workspaces.models import WorkspaceScopedModel
from apps.knowledge.fields import DynamicVectorField


class DocumentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Ingestion"
    PROCESSING = "PROCESSING", "Processing & Chunking"
    READY = "READY", "Ready for Retrieval"
    FAILED = "FAILED", "Ingestion Failed"


class DocumentFileType(models.TextChoices):
    PDF = "PDF", "PDF Document"
    DOCX = "DOCX", "Word Document (.docx)"
    TXT = "TXT", "Plain Text"
    MD = "MD", "Markdown Document"


class KnowledgeBase(WorkspaceScopedModel):
    """
    Workspace-scoped knowledge base collection for organizational documents.
    """

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_knowledge_bases",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_base"
        ordering = ["name"]
        verbose_name = "Knowledge Base"
        verbose_name_plural = "Knowledge Bases"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_workspace_knowledge_base",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.workspace.code})"


class Document(WorkspaceScopedModel):
    """
    Stored document entity tracking file metadata, parsing state, and chunking counts.
    """

    id = models.BigAutoField(primary_key=True)
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="knowledge_documents/%Y/%m/")
    file_type = models.CharField(max_length=10, choices=DocumentFileType.choices)
    file_size = models.IntegerField(default=0, help_text="File size in bytes")
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)
    chunk_count = models.IntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_document"
        ordering = ["-created_at"]
        verbose_name = "Knowledge Document"
        verbose_name_plural = "Knowledge Documents"
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["knowledge_base", "status"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.file_type}] ({self.status})"


class DocumentChunk(WorkspaceScopedModel):
    """
    Discrete semantic text chunk with embedding vector and source citation metadata.
    """

    id = models.BigAutoField(primary_key=True)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.IntegerField()
    content = models.TextField()
    token_count = models.IntegerField(default=0)
    embedding = DynamicVectorField(null=True, blank=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Chunk citations: page_number, heading, source_file",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "knowledge_document_chunk"
        ordering = ["document", "chunk_index"]
        verbose_name = "Document Chunk"
        verbose_name_plural = "Document Chunks"
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="unique_document_chunk_index",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "document"]),
        ]

    def __str__(self):
        return f"Chunk #{self.chunk_index} of {self.document.title}"


class ConversationSession(WorkspaceScopedModel):
    """
    Multi-turn conversation session scoped to an authorized user and active workspace.
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_chat_sessions",
    )
    title = models.CharField(max_length=255, default="Cuộc trò chuyện mới")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_conversation_session"
        ordering = ["-updated_at"]
        verbose_name = "Conversation Session"
        verbose_name_plural = "Conversation Sessions"

    def __str__(self):
        return f"{self.title} [{self.user.username} @ {self.workspace.code}]"


class ChatRole(models.TextChoices):
    USER = "USER", "User"
    ASSISTANT = "ASSISTANT", "AI Assistant"
    SYSTEM = "SYSTEM", "System Grounding Context"


class ChatMessage(WorkspaceScopedModel):
    """
    Individual message in a conversation session with grounded citations and tool logs.
    """

    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=ChatRole.choices)
    content = models.TextField()
    sources = models.JSONField(
        default=list,
        blank=True,
        help_text="Grounded citations: document_title, page_number, similarity",
    )
    tools_used = models.JSONField(
        default=list,
        blank=True,
        help_text="Summary of structured read-only business tools invoked",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_chat_message"
        ordering = ["created_at"]
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"

    def __str__(self):
        return f"[{self.role}] {self.content[:40]}..."
