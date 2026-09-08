"""
REST API ViewSets & Views for Knowledge Base, Documents, Chunks, and AI Chat Assistant.
Enforces workspace isolation, RBAC, and standard platform API envelope.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.workspaces.services import resolve_request_workspace as get_request_workspace
from apps.workspaces.permissions import IsWorkspaceMember
from apps.knowledge.models import (
    KnowledgeBase,
    Document,
    DocumentChunk,
    ConversationSession,
    ChatMessage,
)
from apps.knowledge.serializers import (
    KnowledgeBaseSerializer,
    DocumentSerializer,
    DocumentChunkSerializer,
    ConversationSessionSerializer,
    ChatMessageSerializer,
    ChatQueryRequestSerializer,
)
from apps.knowledge.services import (
    create_knowledge_base,
    upload_and_ingest_document,
    ingest_document,
    delete_document,
    answer_grounded_query,
)
from apps.knowledge.tools import ToolPermissionDenied


def api_response(data=None, error=None, status_code=status.HTTP_200_OK):
    """Standard platform API envelope: {'success': bool, 'data': Any, 'error': Any}"""
    success = error is None and status.is_success(status_code)
    return Response(
        {"success": success, "data": data, "error": error},
        status=status_code,
    )


def check_view_permission(request, workspace, perm_codename: str) -> bool:
    """Verify the platform's custom workspace-scoped RBAC permission."""
    if not request.user or not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    from apps.accounts.services import has_workspace_permission
    return bool(workspace and has_workspace_permission(request.user, workspace, perm_codename))


class KnowledgeBaseListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error={"code": "NO_WORKSPACE", "message": "Active workspace required."}, status_code=status.HTTP_400_BAD_REQUEST)
        
        if not check_view_permission(request, ws, "knowledge.view_knowledge"):
            return api_response(error={"code": "PERMISSION_DENIED", "message": "Permission 'knowledge.view_knowledge' required."}, status_code=status.HTTP_403_FORBIDDEN)

        kb_qs = KnowledgeBase.objects.for_workspace(ws)
        serializer = KnowledgeBaseSerializer(kb_qs, many=True)
        return api_response(data=serializer.data)

    def post(self, request):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error={"code": "NO_WORKSPACE", "message": "Active workspace required."}, status_code=status.HTTP_400_BAD_REQUEST)

        if not check_view_permission(request, ws, "knowledge.manage_knowledge"):
            return api_response(error={"code": "PERMISSION_DENIED", "message": "Permission 'knowledge.manage_knowledge' required."}, status_code=status.HTTP_403_FORBIDDEN)

        name = request.data.get("name")
        if not name or not str(name).strip():
            return api_response(error={"code": "VALIDATION_ERROR", "message": "Field 'name' is required."}, status_code=status.HTTP_400_BAD_REQUEST)

        desc = request.data.get("description", "")
        kb = create_knowledge_base(ws, request.user, name, desc)
        serializer = KnowledgeBaseSerializer(kb)
        return api_response(data=serializer.data, status_code=status.HTTP_201_CREATED)


class KnowledgeBaseDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request, pk):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error={"code": "NO_WORKSPACE", "message": "Active workspace required."}, status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "knowledge.view_knowledge"):
            return api_response(error={"code": "PERMISSION_DENIED", "message": "Permission 'knowledge.view_knowledge' required."}, status_code=status.HTTP_403_FORBIDDEN)

        kb = KnowledgeBase.objects.for_workspace(ws).filter(pk=pk).first()
        if not kb:
            return api_response(error={"code": "NOT_FOUND", "message": "Knowledge base not found."}, status_code=status.HTTP_404_NOT_FOUND)

        serializer = KnowledgeBaseSerializer(kb)
        return api_response(data=serializer.data)

    def delete(self, request, pk):
        ws = get_request_workspace(request)
        if not check_view_permission(request, ws, "knowledge.manage_knowledge"):
            return api_response(error={"code": "PERMISSION_DENIED", "message": "Permission 'knowledge.manage_knowledge' required."}, status_code=status.HTTP_403_FORBIDDEN)

        kb = KnowledgeBase.objects.for_workspace(ws).filter(pk=pk).first()
        if not kb:
            return api_response(error={"code": "NOT_FOUND", "message": "Knowledge base not found."}, status_code=status.HTTP_404_NOT_FOUND)

        kb.delete()
        return api_response(data={"message": f"Knowledge base '{kb.name}' deleted."}, status_code=status.HTTP_200_OK)


class DocumentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error={"code": "NO_WORKSPACE", "message": "Active workspace required."}, status_code=status.HTTP_400_BAD_REQUEST)

        if not check_view_permission(request, ws, "knowledge.view_knowledge"):
            return api_response(error={"code": "PERMISSION_DENIED", "message": "Permission 'knowledge.view_knowledge' required."}, status_code=status.HTTP_403_FORBIDDEN)

        docs = Document.objects.for_workspace(ws).select_related("knowledge_base")
        kb_id = request.query_params.get("knowledge_base_id")
        if kb_id:
            docs = docs.filter(knowledge_base_id=kb_id)

        serializer = DocumentSerializer(docs, many=True)
        return api_response(data=serializer.data)

    def post(self, request):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error={"code": "NO_WORKSPACE", "message": "Active workspace required."}, status_code=status.HTTP_400_BAD_REQUEST)

        if not check_view_permission(request, ws, "knowledge.manage_knowledge"):
            return api_response(error={"code": "PERMISSION_DENIED", "message": "Permission 'knowledge.manage_knowledge' required."}, status_code=status.HTTP_403_FORBIDDEN)

        kb_id = request.data.get("knowledge_base")
        kb = KnowledgeBase.objects.for_workspace(ws).filter(pk=kb_id).first()
        if not kb:
            return api_response(error={"code": "VALIDATION_ERROR", "message": f"Valid knowledge base ID for workspace '{ws.code}' is required."}, status_code=status.HTTP_400_BAD_REQUEST)

        file_obj = request.FILES.get("file")
        if not file_obj:
            return api_response(error={"code": "VALIDATION_ERROR", "message": "No file uploaded in 'file' parameter."}, status_code=status.HTTP_400_BAD_REQUEST)

        title = request.data.get("title") or file_obj.name
        file_type = request.data.get("file_type")
        if not file_type:
            ext = file_obj.name.split(".")[-1].upper()
            file_type = ext if ext in ("PDF", "DOCX", "TXT", "MD") else "TXT"

        try:
            doc = upload_and_ingest_document(
                workspace=ws,
                user=request.user,
                knowledge_base=kb,
                file_obj=file_obj,
                title=title,
                file_type=file_type,
            )
            serializer = DocumentSerializer(doc)
            return api_response(data=serializer.data, status_code=status.HTTP_201_CREATED)
        except Exception as e:
            return api_response(error={"code": "INGESTION_ERROR", "message": str(e)}, status_code=status.HTTP_400_BAD_REQUEST)


class DocumentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request, pk):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error={"code": "NO_WORKSPACE", "message": "Active workspace required."}, status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "knowledge.view_knowledge"):
            return api_response(error={"code": "PERMISSION_DENIED", "message": "Permission 'knowledge.view_knowledge' required."}, status_code=status.HTTP_403_FORBIDDEN)

        doc = Document.objects.for_workspace(ws).select_related("knowledge_base").filter(pk=pk).first()
        if not doc:
            return api_response(error={"code": "NOT_FOUND", "message": "Document not found."}, status_code=status.HTTP_404_NOT_FOUND)

        serializer = DocumentSerializer(doc)
        return api_response(data=serializer.data)

    def delete(self, request, pk):
        ws = get_request_workspace(request)
        if not check_view_permission(request, ws, "knowledge.manage_knowledge"):
            return api_response(error={"code": "PERMISSION_DENIED", "message": "Permission 'knowledge.manage_knowledge' required."}, status_code=status.HTTP_403_FORBIDDEN)

        doc = Document.objects.for_workspace(ws).filter(pk=pk).first()
        if not doc:
            return api_response(error={"code": "NOT_FOUND", "message": "Document not found."}, status_code=status.HTTP_404_NOT_FOUND)

        delete_document(doc, request.user)
        return api_response(data={"message": f"Document '{doc.title}' deleted successfully."})


class DocumentReindexAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def post(self, request, pk):
        ws = get_request_workspace(request)
        if not check_view_permission(request, ws, "knowledge.manage_knowledge"):
            return api_response(error={"code": "PERMISSION_DENIED", "message": "Permission 'knowledge.manage_knowledge' required."}, status_code=status.HTTP_403_FORBIDDEN)

        doc = Document.objects.for_workspace(ws).filter(pk=pk).first()
        if not doc:
            return api_response(error={"code": "NOT_FOUND", "message": "Document not found."}, status_code=status.HTTP_404_NOT_FOUND)

        doc = ingest_document(doc.id)
        serializer = DocumentSerializer(doc)
        return api_response(data=serializer.data)


class DocumentChunkListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request, pk):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error={"code": "NO_WORKSPACE", "message": "Active workspace required."}, status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "knowledge.view_knowledge"):
            return api_response(error={"code": "PERMISSION_DENIED", "message": "Permission 'knowledge.view_knowledge' required."}, status_code=status.HTTP_403_FORBIDDEN)

        doc = Document.objects.for_workspace(ws).filter(pk=pk).first()
        if not doc:
            return api_response(error={"code": "NOT_FOUND", "message": "Document not found."}, status_code=status.HTTP_404_NOT_FOUND)

        chunks = DocumentChunk.objects.for_workspace(ws).filter(document=doc)
        serializer = DocumentChunkSerializer(chunks, many=True)
        return api_response(data=serializer.data)


class ConversationSessionListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error={"code": "NO_WORKSPACE", "message": "Active workspace required."}, status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "ai.chat"):
            return api_response(error={"code": "PERMISSION_DENIED", "message": "Permission 'ai.chat' required."}, status_code=status.HTTP_403_FORBIDDEN)

        sessions = ConversationSession.objects.for_workspace(ws).filter(user=request.user)
        serializer = ConversationSessionSerializer(sessions, many=True)
        return api_response(data=serializer.data)


class ConversationSessionDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request, pk):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error={"code": "NO_WORKSPACE", "message": "Active workspace required."}, status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "ai.chat"):
            return api_response(error={"code": "PERMISSION_DENIED", "message": "Permission 'ai.chat' required."}, status_code=status.HTTP_403_FORBIDDEN)

        session = ConversationSession.objects.for_workspace(ws).filter(pk=pk, user=request.user).first()
        if not session:
            return api_response(error={"code": "NOT_FOUND", "message": "Conversation session not found."}, status_code=status.HTTP_404_NOT_FOUND)

        messages = ChatMessage.objects.for_workspace(ws).filter(session=session)
        serializer = ChatMessageSerializer(messages, many=True)
        return api_response(data={"session_id": session.id, "title": session.title, "messages": serializer.data})


class AIChatAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def post(self, request):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error={"code": "NO_WORKSPACE", "message": "Active workspace required."}, status_code=status.HTTP_400_BAD_REQUEST)

        if not check_view_permission(request, ws, "ai.chat"):
            return api_response(error={"code": "PERMISSION_DENIED", "message": "Permission 'ai.chat' required."}, status_code=status.HTTP_403_FORBIDDEN)

        serializer = ChatQueryRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(error={"code": "VALIDATION_ERROR", "message": serializer.errors}, status_code=status.HTTP_400_BAD_REQUEST)

        msg = serializer.validated_data["message"]
        sess_id = serializer.validated_data.get("session_id")

        try:
            result = answer_grounded_query(
                workspace=ws,
                user=request.user,
                message=msg,
                session_id=sess_id,
            )
            return api_response(data=result)
        except ToolPermissionDenied as e:
            return api_response(error={"code": "PERMISSION_DENIED", "message": str(e)}, status_code=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return api_response(error={"code": "CHAT_ERROR", "message": str(e)}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
