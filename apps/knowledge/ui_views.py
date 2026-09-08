"""
Web UI view handlers for AI Assistant (/ai/) and Knowledge Base (/knowledge/).
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from apps.workspaces.services import resolve_authorized_ui_workspace
from apps.accounts.services import has_workspace_permission
from apps.knowledge.models import (
    KnowledgeBase,
    Document,
    ConversationSession,
    DocumentStatus,
)
from apps.knowledge.services import (
    create_knowledge_base,
    upload_and_ingest_document,
    delete_document,
)


@login_required
def ai_assistant_ui_view(request: HttpRequest) -> HttpResponse:
    """Renders the AI Knowledge Assistant chat interface."""
    ws = resolve_authorized_ui_workspace(request, None, "ai.chat")

    sessions = (
        ConversationSession.objects.for_workspace(ws)
        .filter(user=request.user)
        .order_by("-updated_at")[:20]
    )

    kb_count = KnowledgeBase.objects.for_workspace(ws).count()
    ready_docs_count = Document.objects.for_workspace(ws).filter(status=DocumentStatus.READY).count()

    context = {
        "active_workspace": ws,
        "active_nav": "ai",
        "sessions": sessions,
        "kb_count": kb_count,
        "ready_docs_count": ready_docs_count,
    }
    return render(request, "ai/assistant.html", context)


@login_required
def knowledge_base_ui_view(request: HttpRequest) -> HttpResponse:
    """Renders the Knowledge Base management and document ingestion dashboard."""
    ws = resolve_authorized_ui_workspace(request, None, "knowledge.view_knowledge")
    can_manage = request.user.is_superuser or has_workspace_permission(request.user, ws, "knowledge.manage_knowledge")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create_kb":
            if not can_manage:
                raise PermissionDenied("Missing workspace permission: knowledge.manage_knowledge")
            else:
                name = request.POST.get("name", "").strip()
                desc = request.POST.get("description", "").strip()
                if name:
                    create_knowledge_base(ws, request.user, name, desc)
                    messages.success(request, f"Knowledge base '{name}' created successfully.")
                else:
                    messages.error(request, "Knowledge base name is required.")

        elif action == "upload_doc":
            if not can_manage:
                raise PermissionDenied("Missing workspace permission: knowledge.manage_knowledge")
            else:
                kb_id = request.POST.get("knowledge_base_id")
                kb = KnowledgeBase.objects.for_workspace(ws).filter(pk=kb_id).first()
                file_obj = request.FILES.get("file")
                title = request.POST.get("title", "").strip()

                if kb and file_obj:
                    if not title:
                        title = file_obj.name
                    ext = file_obj.name.split(".")[-1].upper()
                    file_type = ext if ext in ("PDF", "DOCX", "TXT", "MD") else "TXT"

                    doc = upload_and_ingest_document(
                        workspace=ws,
                        user=request.user,
                        knowledge_base=kb,
                        file_obj=file_obj,
                        title=title,
                        file_type=file_type,
                    )
                    if doc.status == DocumentStatus.READY:
                        messages.success(request, f"Document '{doc.title}' ingested successfully ({doc.chunk_count} chunks).")
                    else:
                        messages.warning(request, f"Document uploaded with status: {doc.status}. Error: {doc.error_message}")
                else:
                    messages.error(request, "Please provide a valid knowledge base and document file.")

        return redirect("knowledge_base_ui")

    knowledge_bases = KnowledgeBase.objects.for_workspace(ws).prefetch_related("documents")
    documents = Document.objects.for_workspace(ws).select_related("knowledge_base").order_by("-created_at")

    total_chunks = sum(d.chunk_count for d in documents)

    context = {
        "active_workspace": ws,
        "active_nav": "knowledge",
        "knowledge_bases": knowledge_bases,
        "documents": documents,
        "total_docs": documents.count(),
        "total_chunks": total_chunks,
        "can_manage": can_manage,
    }
    return render(request, "knowledge/index.html", context)
