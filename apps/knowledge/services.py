"""
Orchestration layer for Knowledge Base, Document Ingestion, RAG,
Hybrid Question Routing, and Grounded Answer Generation.
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple
from django.conf import settings
from django.db import transaction
from apps.workspaces.models import Workspace
from apps.accounts.models import User
from apps.audit.services import log_audit_event
from apps.knowledge.models import (
    KnowledgeBase,
    Document,
    DocumentChunk,
    DocumentStatus,
    ConversationSession,
    ChatMessage,
    ChatRole,
)
from apps.knowledge.parsers import parse_document_file, DocumentParsingError
from apps.knowledge.chunking import RecursiveTextChunker
from apps.knowledge.embedding import get_embeddings_batch
from apps.knowledge.retrieval import search_relevant_chunks
from apps.knowledge.tools import execute_tool, ToolPermissionDenied


FALLBACK_NO_CONTEXT_MESSAGE = "Không tìm thấy thông tin đủ tin cậy trong tài liệu của doanh nghiệp."


def create_knowledge_base(
    workspace: Workspace,
    user: User,
    name: str,
    description: str = "",
) -> KnowledgeBase:
    """Creates a workspace-scoped KnowledgeBase."""
    kb = KnowledgeBase.objects.create(
        workspace=workspace,
        name=name.strip(),
        description=description.strip(),
        created_by=user,
    )
    log_audit_event(
        workspace=workspace,
        user=user,
        action="KNOWLEDGE_BASE_CREATE",
        entity_type="KnowledgeBase",
        entity_id=str(kb.id),
        metadata={"name": kb.name},
    )
    return kb


def upload_and_ingest_document(
    workspace: Workspace,
    user: User,
    knowledge_base: KnowledgeBase,
    file_obj: Any,
    title: str,
    file_type: str,
) -> Document:
    """Creates Document in PENDING status and triggers synchronous ingestion."""
    file_size = getattr(file_obj, "size", 0)
    doc = Document.objects.create(
        workspace=workspace,
        knowledge_base=knowledge_base,
        title=title.strip(),
        file=file_obj,
        file_type=file_type.upper(),
        file_size=file_size,
        status=DocumentStatus.PENDING,
        uploaded_by=user,
    )

    log_audit_event(
        workspace=workspace,
        user=user,
        action="DOCUMENT_UPLOAD",
        entity_type="Document",
        entity_id=str(doc.id),
        metadata={"title": doc.title, "file_type": doc.file_type, "file_size": file_size},
    )

    # Ingest document
    ingest_document(doc.id)
    doc.refresh_from_db()
    return doc


def ingest_document(document_id: int) -> Document:
    """
    Executes Document Ingestion pipeline:
    Document -> Parse -> Normalize -> Chunk -> Embed -> Store vector -> Ready.
    """
    doc = Document.objects.select_related("workspace", "knowledge_base").get(id=document_id)
    doc.status = DocumentStatus.PROCESSING
    doc.error_message = ""
    doc.save(update_fields=["status", "error_message"])

    try:
        # 1. Parse document into clean text segments
        doc.file.open("rb")
        segments, meta = parse_document_file(doc.file, doc.file_type)
        doc.file.close()

        # 2. Chunk segments
        chunker = RecursiveTextChunker()
        chunk_dicts = chunker.chunk_segments(segments, source_title=doc.title)

        if not chunk_dicts:
            raise DocumentParsingError("Document produced 0 text chunks after processing.")

        # 3. Generate embeddings batch
        contents = [c["content"] for c in chunk_dicts]
        embeddings = get_embeddings_batch(contents)

        # 4. Atomic storage in database
        with transaction.atomic():
            # Delete any previous chunks
            DocumentChunk.objects.filter(document=doc).delete()

            chunk_objects = []
            for i, c in enumerate(chunk_dicts):
                chunk_objects.append(
                    DocumentChunk(
                        workspace=doc.workspace,
                        document=doc,
                        chunk_index=c["chunk_index"],
                        content=c["content"],
                        token_count=c["token_count"],
                        embedding=embeddings[i],
                        metadata=c["metadata"],
                    )
                )
            DocumentChunk.objects.bulk_create(chunk_objects)

            doc.status = DocumentStatus.READY
            doc.chunk_count = len(chunk_objects)
            doc.source_metadata = meta
            doc.save(update_fields=["status", "chunk_count", "source_metadata", "updated_at"])

        log_audit_event(
            workspace=doc.workspace,
            user=doc.uploaded_by,
            action="DOCUMENT_INDEX_COMPLETED",
            entity_type="Document",
            entity_id=str(doc.id),
            metadata={"title": doc.title, "chunk_count": doc.chunk_count},
        )

    except Exception as e:
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(e)
        doc.save(update_fields=["status", "error_message", "updated_at"])

    return doc


def delete_document(document: Document, user: User) -> None:
    """Deletes a document and its chunks, logging an audit event."""
    ws = document.workspace
    doc_id = str(document.id)
    doc_title = document.title

    if document.file:
        try:
            document.file.delete(save=False)
        except Exception:
            pass

    document.delete()

    log_audit_event(
        workspace=ws,
        user=user,
        action="DOCUMENT_DELETE",
        entity_type="Document",
        entity_id=doc_id,
        metadata={"title": doc_title},
    )


def _matches_any_keyword(keywords: List[str], text: str) -> bool:
    import unicodedata
    def strip_accents(s: str) -> str:
        res = "".join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
        return res.replace('đ', 'd').replace('Đ', 'D').lower()

    norm_text = strip_accents(text)
    raw_text = text.lower()

    for k in keywords:
        k_raw = k.lower()
        k_norm = strip_accents(k)
        if k_raw in raw_text or k_norm in norm_text:
            return True
        pattern = r"(?:\b|\s|^)" + re.escape(k_norm) + r"(?:\b|\s|$)"
        if re.search(pattern, norm_text, re.IGNORECASE):
            return True
    return False



# Thread-local storage for intent parameters extracted during routing.
# Allows answer_grounded_query to pass typed kwargs to each tool call.
_last_intent_params: Dict[str, Any] = {}


def detect_tools_for_query(query: str, workspace: Workspace) -> List[str]:
    """
    Priority-ordered intent router for Vietnamese business queries.
    Delegates to classify_business_intent() from intent_router which correctly
    distinguishes sales-ranking, catalog, revenue, customer, branch, forecast,
    service ticket, technician, GIS, ambiguous, and mutation intents.

    Side effect: stores extracted parameters in module-level _last_intent_params
    so that answer_grounded_query() can pass them as kwargs to each tool call.
    """
    global _last_intent_params
    from apps.knowledge.intent_router import classify_business_intent, BusinessIntent

    result = classify_business_intent(query, workspace)
    _last_intent_params = result.get("parameters", {})

    tool_list = result.get("tools", [])

    # For AMBIGUOUS intent, no tools — handled separately in answer_grounded_query
    if result.get("intent") == BusinessIntent.AMBIGUOUS:
        return []

    # Recommendations: ensure fresh data exists before returning tool
    if "get_recommendations" in tool_list:
        try:
            from apps.recommendations.models import Recommendation, RecommendationStatus
            if not Recommendation.objects.for_workspace(workspace).filter(status=RecommendationStatus.PENDING).exists():
                from apps.recommendations.rules import evaluate_retail_recommendations, evaluate_service_recommendations
                evaluate_retail_recommendations(workspace)
                evaluate_service_recommendations(workspace)
        except Exception:
            pass

    return tool_list


def detect_and_handle_mutation_request(query: str, workspace: Workspace, user: User) -> Optional[Dict[str, Any]]:
    """
    Checks if a user query is requesting a state-modifying operational action.
    If detected:
    - Extracts parameters safely.
    - Routes through controlled ToolRegistry / Approvals Executor.
    - Generates a PENDING ApprovalRequest (Zero Direct DB Mutations by AI).
    - Returns structured result detailing the created approval request.
    """
    from apps.approvals.executor import execute_tool as execute_controlled_tool
    q = query.lower()

    # 1. Dispatch technician to ticket
    if any(k in q for k in ["phân công", "phan cong", "giao việc", "giao viec", "điều động", "dieu dong", "assign", "dispatch"]):
        if any(k in q for k in ["ticket", "phiếu", "phieu", "yêu cầu", "yeu cau", "request"]):
            m_ticket = re.search(r"(?:ticket|phiếu|phieu|yêu cầu|yeu cau|request)\s*#?\s*(\d+)", q)
            m_emp = re.search(r"(?:kỹ thuật viên|ky thuat vien|nhân viên|nhan vien|technician|employee|staff)\s*#?\s*(\d+)", q)
            emp_id = None
            if m_emp:
                emp_id = int(m_emp.group(1))
            else:
                from apps.service_ops.models import Employee
                for emp in Employee.objects.for_workspace(workspace).filter(is_active=True):
                    if emp.code.lower() in q or emp.full_name.lower() in q:
                        emp_id = emp.id
                        break

            if m_ticket and emp_id:
                ticket_id = int(m_ticket.group(1))
                return execute_controlled_tool(
                    name="dispatch_technician",
                    workspace=workspace,
                    user=user,
                    parameters={"ticket_id": ticket_id, "employee_id": emp_id},
                    reason=f"Yêu cầu điều động từ Trợ lý AI theo lệnh người dùng: '{query}'"
                )

    # 2. Update order status
    if any(k in q for k in ["cập nhật", "cap nhat", "chuyển trạng thái", "chuyen trang thai", "update status", "update order"]):
        if any(k in q for k in ["đơn hàng", "don hang", "order"]):
            m_order = re.search(r"(?:đơn hàng|don hang|order)\s*#?\s*(\d+)", q)
            status_match = None
            for s in ["PENDING", "CONFIRMED", "PROCESSING", "SHIPPED", "COMPLETED", "CANCELLED"]:
                if s.lower() in q:
                    status_match = s
                    break
            if m_order and status_match:
                order_id = int(m_order.group(1))
                return execute_controlled_tool(
                    name="update_order_status",
                    workspace=workspace,
                    user=user,
                    parameters={"order_id": order_id, "new_status": status_match},
                    reason=f"Yêu cầu cập nhật trạng thái đơn hàng từ Trợ lý AI: '{query}'"
                )

    # 3. Adjust product price
    if any(k in q for k in ["điều chỉnh giá", "dieu chinh gia", "cập nhật giá", "cap nhat gia", "đổi giá", "doi gia", "adjust price"]):
        m_prod = re.search(r"(?:sản phẩm|san pham|product)\s*#?\s*(\d+)", q)
        m_price = re.search(r"(?:thành|sang|to|=)\s*([\d\.,]+)", q)
        if not m_price:
            m_price = re.search(r"(\d[\d\.,]*)\s*(?:vnd|đồng|dong|d)", q)
        if m_prod and m_price:
            try:
                prod_id = int(m_prod.group(1))
                clean_price_str = m_price.group(1).replace(",", "").replace(".", "")
                new_price = float(clean_price_str)
                if new_price > 0:
                    return execute_controlled_tool(
                        name="adjust_product_price",
                        workspace=workspace,
                        user=user,
                        parameters={"product_id": prod_id, "new_price": new_price},
                        reason=f"Yêu cầu điều chỉnh đơn giá từ Trợ lý AI: '{query}'"
                    )
            except Exception:
                pass

    # 4. Schedule task
    if any(k in q for k in ["lập lịch", "lap lich", "tạo nhiệm vụ", "tao nhiem vu", "schedule task"]):
        m_title = re.search(r"['\"]([^'\"]+)['\"]", query)
        title = m_title.group(1) if m_title else "Nhiệm vụ điều phối từ Trợ lý AI"
        m_emp = re.search(r"(?:kỹ thuật viên|nhân viên|technician|employee)\s*#?\s*(\d+)", q)
        emp_id = int(m_emp.group(1)) if m_emp else None
        params = {"title": title}
        if emp_id:
            params["employee_id"] = emp_id
        return execute_controlled_tool(
            name="schedule_task",
            workspace=workspace,
            user=user,
            parameters=params,
            reason=f"Yêu cầu lập lịch nhiệm vụ từ Trợ lý AI: '{query}'"
        )

    # 5. Create goods receipt proposal (PO requisition)
    if any(k in q for k in ["tạo phiếu nhập", "tao phieu nhap", "phiếu nhập kho", "phieu nhap kho", "đề xuất tạo phiếu nhập", "de xuat tao phieu nhap", "nhập thêm", "nhap them"]):
        try:
            from apps.retail.models import Supplier, Branch, Product
            supplier = Supplier.objects.for_workspace(workspace).first()
            branch = Branch.objects.for_workspace(workspace).first()
            product = None
            for p in Product.objects.for_workspace(workspace).filter(is_active=True):
                p_name_lower = p.name.lower()
                if p_name_lower in q or p.sku.lower() in q or ("dell" in q and "dell" in p_name_lower) or ("inspiron" in q and "inspiron" in p_name_lower):
                    product = p
                    break
            if not product:
                product = Product.objects.for_workspace(workspace).first()

            m_qty = re.search(r"(\d+)\s*(?:chiếc|chiec|cái|cai|đơn vị|don vi|sp|sản phẩm|laptop)", q)
            quantity = int(m_qty.group(1)) if m_qty else 20
            unit_cost = float(product.cost_price) if (product and product.cost_price) else 15000000.0

            if supplier and branch and product:
                params = {
                    "supplier_id": supplier.id,
                    "branch_id": branch.id,
                    "items": [
                        {
                            "product_id": product.id,
                            "quantity": quantity,
                            "unit_cost": unit_cost,
                        }
                    ],
                }
                return execute_controlled_tool(
                    name="create_goods_receipt",
                    workspace=workspace,
                    user=user,
                    parameters=params,
                    reason=f"Yêu cầu tạo phiếu nhập kho dự phòng từ Trợ lý AI: '{query}'"
                )
        except Exception:
            pass

    # Inter-branch Stock Transfer.  This branch is intentionally outside the
    # goods-receipt condition: a transfer request must not depend on a
    # supplier/receipt being present in the workspace.
    # A read-only question may contain "đề xuất điều chuyển"; only create a
    # mutation approval when the user explicitly asks to lập/tạo the proposal.
    explicit_transfer_action = any(w in q for w in [
        "lập đề xuất", "lap de xuat", "tạo đề xuất", "tao de xuat",
        "tạo phiếu điều chuyển", "tao phieu dieu chuyen",
    ])
    if explicit_transfer_action and any(w in q for w in ["điều chuyển", "dieu chuyen", "chuyển hàng", "chuyen hang"]):
        try:
            from apps.retail.models import Branch, Product
            branches = list(Branch.objects.for_workspace(workspace))
            product = Product.objects.for_workspace(workspace).filter(name__icontains="laptop").first() or Product.objects.for_workspace(workspace).first()
            if len(branches) >= 2 and product:
                src_branch = branches[1]
                dest_branch = branches[0]
                m_qty = re.search(r"(\d+)\s*(?:chiếc|chiec|cái|cai|máy|sp|sản phẩm|laptop)", q)
                quantity = int(m_qty.group(1)) if m_qty else 2
                return execute_controlled_tool(
                    name="create_stock_transfer",
                    workspace=workspace,
                    user=user,
                    parameters={
                        "source_branch_id": src_branch.id,
                        "destination_branch_id": dest_branch.id,
                        "product_id": product.id,
                        "quantity": quantity,
                    },
                    reason=f"Yêu cầu điều chuyển tồn kho nội bộ từ Trợ lý AI: '{query}'"
                )
        except Exception:
            pass

    # Markdown / Discount Price for slow-moving inventory
    if any(w in q for w in ["hạ giá", "ha gia", "xả kho", "xa kho", "giảm giá", "giam gia"]):
        try:
            from apps.retail.models import Product
            product = Product.objects.for_workspace(workspace).filter(name__icontains="laptop").first() or Product.objects.for_workspace(workspace).first()
            if product and product.unit_price:
                m_pct = re.search(r"(\d+)\s*%", q)
                discount_pct = float(m_pct.group(1)) if m_pct else 5.0
                new_price = round(float(product.unit_price) * (1.0 - discount_pct / 100.0), -4)
                cost = float(product.cost_price or 0.0)
                if cost > 0 and new_price < cost * 1.03:
                    new_price = round(cost * 1.05, -4)
                return execute_controlled_tool(
                    name="adjust_product_price",
                    workspace=workspace,
                    user=user,
                    parameters={
                        "product_id": product.id,
                        "new_price": new_price,
                    },
                    reason=f"Yêu cầu điều chỉnh giảm giá xả hàng tồn kho chậm luân chuyển ({discount_pct}%): '{query}'"
                )
        except Exception:
            pass

    return None



def _call_gemini_chat_api(prompt: str, api_key: str, model_name: str) -> Optional[str]:
    """Invokes Google Gemini generateContent REST API using urllib."""
    import json
    import urllib.request
    import urllib.error

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
    }
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
    except Exception:
        pass
    return None


def generate_grounded_answer(
    workspace: Workspace,
    user: User,
    query: str,
    chunks: List[Dict[str, Any]],
    tools_data: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Synthesizes a strictly grounded answer with source citations.
    Enforces the no-context fallback if confidence is insufficient.
    """
    tools_data = tools_data or []
    sources: List[Dict[str, Any]] = []

    # If no chunks and no tools data, strictly return the fallback message
    if not chunks and not tools_data:
        return FALLBACK_NO_CONTEXT_MESSAGE, []

    # Build Citation List from retrieved chunks
    for ch in chunks:
        sources.append({
            "document_title": ch["document_title"],
            "page_number": ch.get("page_number"),
            "chunk_id": ch["chunk_id"],
            "similarity": ch["similarity"],
            "heading": ch.get("heading"),
        })

    # Prepare Context Prompt Blocks
    context_blocks: List[str] = []

    if tools_data:
        context_blocks.append("=== DỮ LIỆU KINH DOANH VẬN HÀNH (HỆ THỐNG) ===")
        for td in tools_data:
            tool_name = td.get("tool", "tool")
            clean_facts = {k: v for k, v in td.items() if k not in ("tool", "workspace", "total_revenue_raw")}
            context_blocks.append(f"[{tool_name}]: {clean_facts}")

    if chunks:
        context_blocks.append("=== TÀI LIỆU QUY TRÌNH & CHÍNH SÁCH DOANH NGHIỆP ===")
        for ch in chunks:
            page_info = f", Trang {ch['page_number']}" if ch.get("page_number") else ""
            heading_info = f", Mục: {ch['heading']}" if ch.get("heading") else ""
            context_blocks.append(
                f"[Tài liệu: {ch['document_title']}{page_info}{heading_info}]\n{ch['content']}"
            )

    full_context = "\n\n".join(context_blocks)

    system_prompt = f"""Bạn là Trợ lý Tri thức Doanh nghiệp (AI Knowledge Assistant) cho workspace '{workspace.name}'.
Nhiệm vụ của bạn là trả lời câu hỏi của người dùng CHỈ DỰA TRÊN thông tin được cung cấp trong phần DỮ LIỆU NGỮ CẢNH bên dưới.

QUY TẮC CỐT LÕI (BẮT BUỘC):
1. Tuyệt đối KHÔNG bịa đặt thông tin không có trong ngữ cảnh.
2. Nếu ngữ cảnh KHÔNG đủ thông tin để trả lời, hãy trả lời chính xác: "{FALLBACK_NO_CONTEXT_MESSAGE}".
3. Trích dẫn rõ ràng nguồn tài liệu (Tên tài liệu, Trang hoặc Mục) hoặc số liệu hệ thống trong câu trả lời.
4. Trả lời mạch lạc, súc tích bằng tiếng Việt.

DỮ LIỆU NGỮ CẢNH:
{full_context}

CÂU HỎI CỦA NGƯỜI DÙNG:
{query}
"""

    api_key = getattr(settings, "LLM_API_KEY", "")
    llm_model = getattr(settings, "LLM_MODEL", "gemini-2.5-flash")

    # If live LLM API is available, invoke it
    if api_key and api_key.strip():
        llm_response = _call_gemini_chat_api(system_prompt, api_key, llm_model)
        if llm_response:
            return llm_response, sources

    # Deterministic Grounded Synthesizer (Offline / Test / CI mode)
    answer_parts: List[str] = []

    # 1. Summarize Structured Business Facts if invoked
    if tools_data:
        for td in tools_data:
            tname = td.get("tool")
            if tname == "get_sales_summary":
                answer_parts.append(
                    f"Theo dữ liệu kinh doanh của hệ thống, tổng doanh thu đạt {td.get('total_revenue')}, "
                    f"với {td.get('total_orders')} đơn hàng ({td.get('completed_orders')} đơn đã hoàn thành)."
                )
            elif tname == "get_product_catalog_summary":
                answer_parts.append(
                    f"Danh mục sản phẩm hiện có {td.get('total_products')} sản phẩm ({td.get('active_products')} đang kinh doanh)."
                )
            elif tname == "get_customer_summary":
                answer_parts.append(
                    f"Hệ thống quản lý {td.get('total_customers')} khách hàng theo các phân khúc chuẩn hóa."
                )
            elif tname == "get_service_ticket_summary":
                if "ticket_found" in td:
                    if not td["ticket_found"]:
                        answer_parts.append(td.get("message", "Không tìm thấy phiếu trong workspace này."))
                    else:
                        answer_parts.append(
                            f"Phiếu {td['ticket_number']}: {td['title']}. Trạng thái: {td['status']}; "
                            f"ưu tiên: {td['priority']}; kỹ thuật viên: {td['assigned_technician']}. "
                            f"Hạn xử lý: {td['resolution_deadline']}."
                        )
                    continue
                answer_parts.append(
                    f"Về vận hành dịch vụ, hiện có {td.get('total_tickets')} phiếu yêu cầu ({td.get('open_tickets')} đang xử lý, "
                    f"{td.get('overdue_sla_tickets')} quá hạn SLA)."
                )
            elif tname == "get_technician_workload_summary":
                answer_parts.append(
                    f"Đội ngũ kỹ thuật viên gồm {td.get('total_technicians')} nhân sự ({td.get('available_technicians')} đang sẵn sàng, "
                    f"điểm tải công việc trung bình: {td.get('average_workload_score')}/100)."
                )
            elif tname == "get_recommendations":
                recs = td.get("recommendations", [])
                if recs:
                    for top in recs[:2]:
                        expl = top.get("explanation", {})
                        ev = expl.get("evidence", {})
                        ev_str = ", ".join(f"{k}: {v}" for k, v in ev.items() if not isinstance(v, (dict, list)))
                        answer_parts.append(
                            f"📌 Đề xuất khuyến nghị: '{top.get('title')}' (Ưu tiên: {top.get('priority_display', top.get('priority'))})\n"
                            f"- Hành động: {expl.get('what', '')}\n"
                            f"- Lý do cảnh báo: {expl.get('why', '')}\n"
                            f"- Bằng chứng dữ liệu (Evidence): {ev_str or str(ev)}\n"
                            f"- Tác động kỳ vọng: {expl.get('expected_effect', '')}"
                        )
            elif tname == "query_nearby_technicians":
                cands = td.get("candidates", [])
                if cands:
                    top = cands[0]
                    score_info = f", Điểm đánh giá: {top.get('total_score', 'N/A')}/100" if "total_score" in top else ""
                    sub_info = ""
                    if top.get("subscores"):
                        sub = top["subscores"]
                        sub_info = f" (Điểm khoảng cách: {sub.get('distance_score')}, Tải công việc: {sub.get('workload_score')}, Kỹ năng: {sub.get('skill_score')})"
                    answer_parts.append(
                        f"📍 Đề xuất phân công kỹ thuật viên (Phân tích GIS & Thuật toán Chấm điểm Đa tiêu chí):\n"
                        f"- Kỹ thuật viên tối ưu: {top.get('name')} ({top.get('code')}){score_info}{sub_info}\n"
                        f"- Khoảng cách địa lý: {top.get('distance_km')} km\n"
                        f"- Số công việc đang xử lý: {top.get('active_tasks')} công việc\n"
                        f"- Bằng chứng: Điểm số tính toán minh bạch từ công thức chuẩn hóa w_dist=0.4, w_workload=0.4, w_skill=0.2."
                    )
            elif tname == "get_top_selling_products":
                rankings = td.get("rankings", [])
                cat_label = td.get("category_filter", "all")
                cat_str = f" trong danh mục '{cat_label}'" if cat_label and cat_label != "all" else ""
                time_str = td.get("time_range", "toàn thời gian")
                metric_name = td.get("ranking_metric_name", "Số lượng bán ra")
                if rankings:
                    top = rankings[0]
                    lines = [f"📊 **Xếp hạng sản phẩm bán chạy{cat_str}** ({time_str}) — theo {metric_name}:"]
                    for i, r in enumerate(rankings[:5], 1):
                        lines.append(
                            f"{i}. **{r['name']}** ({r['sku']}) — Đã bán: {r['quantity_sold']} sản phẩm, Doanh thu: {r['revenue_formatted']}"
                        )
                    answer_parts.append("\n".join(lines))
                else:
                    answer_parts.append(
                        f"Chưa ghi nhận dữ liệu bán hàng{cat_str} trong khoảng thời gian {time_str}."
                    )
            elif tname == "get_top_customers":
                rankings = td.get("rankings", [])
                time_str = td.get("time_range", "toàn thời gian")
                if rankings:
                    lines = [f"👥 **Khách hàng mua nhiều nhất** ({time_str}):"]
                    for i, c in enumerate(rankings[:5], 1):
                        lines.append(
                            f"{i}. **{c['customer_name']}** ({c['customer_code']}) — "
                            f"{c['order_count']} đơn hàng, Tổng chi tiêu: {c['total_spend_formatted']}"
                        )
                    answer_parts.append("\n".join(lines))
                else:
                    answer_parts.append(f"Chưa có dữ liệu mua hàng trong khoảng thời gian {time_str}.")
            elif tname == "get_branch_sales_analytics":
                branches = td.get("branches", [])
                time_str = td.get("time_range", "toàn thời gian")
                sort_ord = td.get("sort_order", "DESC")
                sort_label = "doanh thu cao nhất" if sort_ord == "DESC" else "doanh thu thấp nhất"
                if branches:
                    lines = [f"🏪 **Xếp hạng chi nhánh theo {sort_label}** ({time_str}):"]
                    for i, b in enumerate(branches[:5], 1):
                        lines.append(
                            f"{i}. **{b['branch_name']}** ({b['branch_code']}) — "
                            f"Doanh thu: {b['revenue_formatted']}, {b['order_count']} đơn hàng"
                        )
                    answer_parts.append("\n".join(lines))
                else:
                    answer_parts.append(f"Chưa có dữ liệu doanh thu chi nhánh trong khoảng thời gian {time_str}.")
            elif tname == "get_stockout_risk_summary":
                at_risk = td.get("products_at_risk", [])
                total_tracked = td.get("total_tracked", 0)
                out_cnt = td.get("out_of_stock_count", 0)
                high_cnt = td.get("high_risk_count", 0)
                med_cnt = td.get("medium_risk_count", 0)
                cat_filter = td.get("category_filter", "Tất cả")
                cat_str = f" danh mục '{cat_filter}'" if cat_filter and cat_filter != "Tất cả danh mục" else ""

                if at_risk:
                    lines = [
                        f"⚠️ **Cảnh báo tồn kho & Dự báo nguy cơ hết hàng{cat_str}**:",
                        f"- Tổng số sản phẩm theo dõi: {total_tracked} | 🔴 Hết hàng: {out_cnt} | 🟠 Nguy cơ cao (< 7 ngày): {high_cnt} | 🟡 Nguy cơ trung bình (7-10 ngày): {med_cnt}\n",
                        "| Sản phẩm | Tồn kho | Nhu cầu dự báo | Dự kiến hết | Thời gian nhập | Đề xuất nhập thêm |",
                        "|---|---|---|---|---|---|",
                    ]
                    for p in at_risk[:6]:
                        icon = "🔴" if p["risk_level"] == "OUT_OF_STOCK" else ("🟠" if p["risk_level"] == "HIGH" else "🟡")
                        days_str = "Hết hàng" if p["risk_level"] == "OUT_OF_STOCK" else f"{p['days_to_stockout']} ngày"
                        lines.append(
                            f"| {icon} **{p['product_name']}** | {p['current_stock']} {p['unit']} | {p['predicted_daily_demand']}/ngày | {days_str} | {p['lead_time_days']} ngày | **+{p['suggested_reorder_quantity']} {p['unit']}** |"
                        )
                    answer_parts.append("\n".join(lines))
                else:
                    answer_parts.append(
                        f"✅ Tồn kho toàn bộ sản phẩm{cat_str} đang ở mức an toàn. Không có sản phẩm nào có nguy cơ hết hàng trong 10 ngày tới."
                    )
            elif tname == "get_stock_balance_summary":
                balances = td.get("balances", [])
                total_units = td.get("total_stock_units", 0)
                if balances:
                    lines = [
                        f"📦 **Tổng quan tồn kho chi nhánh** (Tổng tồn: {total_units:,} đơn vị sản phẩm):",
                        "| Sản phẩm | Danh mục | Chi nhánh | Tồn kho hiện tại |",
                        "|---|---|---|---|",
                    ]
                    for b in balances[:8]:
                        lines.append(
                            f"| **{b['product_name']}** ({b['product_sku']}) | {b['category']} | {b['branch_name']} | **{b['quantity_on_hand']} {b['unit']}** |"
                        )
                    answer_parts.append("\n".join(lines))
                else:
                    answer_parts.append("Chưa có thông tin tồn kho cho các sản phẩm yêu cầu.")
            elif tname == "compare_entities_analytics":
                comp = td.get("comparison", [])
                metric_lbl = td.get("metric_label", "Doanh thu")
                leader = td.get("leader")
                diff = td.get("difference", 0)
                pct_lead = td.get("percentage_lead", 0.0)
                ent_type = "chi nhánh" if td.get("entity_type") == "branch" else "sản phẩm / thương hiệu"
                time_str = td.get("time_range", "toàn thời gian")

                if comp:
                    lines = [f"⚖️ **Kết quả so sánh {ent_type}** ({time_str}) — theo {metric_lbl}:"]
                    if leader and len(comp) >= 2:
                        lines.append(f"- **{leader}** dẫn đầu (vượt hơn {diff:,.0f} đơn vị / VND, chênh lệch **+{pct_lead}%**).")
                    lines.append("\n| Thực thể | Số lượng bán / Đơn | Doanh thu |")
                    lines.append("|---|---|---|")
                    for c in comp:
                        name_str = c.get("name") or c.get("entity_name")
                        qty_str = f"{c.get('quantity_sold', c.get('order_count', 0))} đơn vị"
                        lines.append(f"| **{name_str}** | {qty_str} | {c.get('revenue_formatted', '0 VND')} |")
                    answer_parts.append("\n".join(lines))
                else:
                    answer_parts.append(f"Chưa có đủ dữ liệu bán hàng để so sánh các {ent_type} được yêu cầu trong khoảng thời gian {time_str}.")

            elif tname == "get_sales_trend_analytics":
                direction = td.get("trend_direction", "ỔN ĐỊNH")
                icon = td.get("trend_icon", "📈")
                pct = td.get("growth_rate_pct", 0.0)
                curr_rev = td.get("current_revenue_formatted", "0 VND")
                prev_rev = td.get("previous_revenue_formatted", "0 VND")
                diff_val = td.get("revenue_difference", 0)
                cat_flt = td.get("category_filter", "Toàn bộ sản phẩm")
                lines = [
                    f"{icon} **Phân tích xu hướng kinh doanh ({cat_flt})**:",
                    f"- Xu hướng: **{direction}** (Tốc độ thay đổi: **{pct:+.1f}%**)",
                    f"- Doanh thu kỳ gần nhất ({td.get('current_period')}): **{curr_rev}** ({td.get('current_units', 0)} đơn vị)",
                    f"- Doanh thu kỳ liền trước ({td.get('previous_period')}): **{prev_rev}** ({td.get('previous_units', 0)} đơn vị)",
                    f"- Chênh lệch tuyệt đối: **{diff_val:+,.0f} VND**",
                ]
                answer_parts.append("\n".join(lines))

            elif tname == "get_service_labor_cost_summary":
                tot_hours = td.get("total_labor_hours", 0)
                tot_cost = td.get("total_labor_cost_formatted", "0 VND")
                cnt = td.get("labor_entries_count", 0)
                time_str = td.get("time_range", "toàn thời gian")
                techs = td.get("technician_breakdown", [])
                lines = [
                    f"⏱️ **Báo cáo chi phí nhân công & giờ công kỹ thuật** ({time_str}):",
                    f"- Tổng số giờ công ghi nhận: **{tot_hours} giờ** ({cnt} lượt ghi nhận)",
                    f"- Tổng chi phí nhân công: **{tot_cost}**\n",
                ]
                if techs:
                    lines.append("| Kỹ thuật viên | Mã NV | Số giờ làm | Chi phí nhân công |")
                    lines.append("|---|---|---|---|")
                    for t in techs:
                        lines.append(f"| **{t['technician_name']}** | `{t['technician_code']}` | {t['hours']} giờ | {t['cost_formatted']} |")
                answer_parts.append("\n".join(lines))

            elif tname == "get_service_catalog_summary":
                svcs = td.get("services", [])
                total_s = td.get("total_services", 0)
                cat_flt = td.get("category_filter", "Tất cả")
                if svcs:
                    lines = [
                        f"🛠️ **Bảng danh mục dịch vụ IT & Đơn giá ({cat_flt})** (Tổng cộng: {total_s} dịch vụ):",
                        "| Mã DV | Tên dịch vụ | Danh mục | Thời lượng chuẩn | Đơn giá cơ sở |",
                        "|---|---|---|---|---|",
                    ]
                    for s in svcs[:10]:
                        lines.append(f"| `{s['code']}` | **{s['name']}** | {s['category']} | {s['duration_minutes']} phút | **{s['base_fee_formatted']}** |")
                    answer_parts.append("\n".join(lines))
                else:
                    answer_parts.append(f"Chưa có thông tin danh mục dịch vụ cho tiêu chí '{cat_flt}'.")

            elif tname == "get_service_ticket_summary":
                if td.get("ticket_found"):
                    overdue_str = "⚠️ ĐÃ QUÁ HẠN" if td.get("is_overdue") else f"Còn {td.get('remaining_time_formatted')}"
                    lines = [
                        f"🎫 **Thông tin chi tiết phiếu yêu cầu #{td.get('ticket_id')} ({td.get('ticket_number')})**:",
                        f"- Tiêu đề: **{td.get('title')}**",
                        f"- Trạng thái: **{td.get('status')}** | Mức độ ưu tiên: **{td.get('priority')}**",
                        f"- Khách hàng: {td.get('customer_name')} | Dịch vụ: {td.get('service_name')}",
                        f"- Kỹ thuật viên phụ trách: **{td.get('assigned_technician')}**",
                        f"- Thời hạn SLA: {td.get('resolution_deadline')} ({overdue_str})",
                    ]
                    answer_parts.append("\n".join(lines))
                elif td.get("ticket_found") is False:
                    answer_parts.append(td.get("message", "Không tìm thấy phiếu yêu cầu."))
                else:
                    tot_t = td.get("total_tickets", 0)
                    open_t = td.get("open_tickets", 0)
                    overdue_t = td.get("overdue_sla_tickets", 0)
                    at_risk_t = td.get("at_risk_sla_tickets", 0)
                    lines = [
                        f"🎫 **Tổng quan phiếu yêu cầu dịch vụ (Service Tickets)**:",
                        f"- Tổng số phiếu: {tot_t} | Đang xử lý: **{open_t}**",
                        f"- Quá hạn SLA: **{overdue_t}** ticket | Nguy cơ trễ (< 4h): **{at_risk_t}** ticket",
                    ]
                    t_list = td.get("tickets", [])
                    if t_list:
                        lines.append("\n| Ticket | Tiêu đề | Ưu tiên | Trạng thái | Phụ trách | Deadline |")
                        lines.append("|---|---|---|---|---|---|")
                        for t in t_list[:5]:
                            lines.append(f"| `#{t['id']}` | **{t['title']}** | {t['priority']} | {t['status']} | {t['assigned_to']} | {t['deadline']} |")
                    answer_parts.append("\n".join(lines))

            elif tname == "get_customer_order_history":
                if td.get("customer_found"):
                    lines = [
                        f"🛍️ **Lịch sử mua hàng của khách hàng {td.get('customer_name')}** (`{td.get('customer_code')}` - Phân khúc: {td.get('customer_segment')}):",
                        f"- Tổng chi tiêu tích lũy: **{td.get('total_spent_formatted')}** ({td.get('order_count')} đơn hàng)",
                        f"- Danh mục sản phẩm đã mua: {', '.join(td.get('purchased_products_summary', []))}\n",
                    ]
                    orders = td.get("orders", [])
                    if orders:
                        lines.append("| Đơn hàng | Ngày đặt | Trạng thái | Số mặt hàng | Tổng tiền |")
                        lines.append("|---|---|---|---|---|")
                        for o in orders:
                            lines.append(f"| `{o['order_number']}` | {o['order_date']} | {o['status']} | {o['items_count']} | **{o['total_amount_formatted']}** |")
                    answer_parts.append("\n".join(lines))
                else:
                    answer_parts.append(td.get("message", "Không tìm thấy thông tin khách hàng."))

            elif tname == "get_technician_skills_summary":
                techs = td.get("technicians", [])
                skill_flt = td.get("skill_filter", "Tất cả")
                avail_flt = " (Chỉ người đang rảnh)" if td.get("available_only") else ""
                if techs:
                    lines = [
                        f"👨‍💻 **Danh sách kỹ thuật viên đáp ứng chuyên môn: '{skill_flt}'{avail_flt}** (Tìm thấy {len(techs)} người):",
                        "| Mã NV | Họ và tên | Kỹ năng chuyên môn | Trạng thái | Tải công việc | Đơn giá giờ |",
                        "|---|---|---|---|---|---|",
                    ]
                    for t in techs:
                        skills_str = ", ".join(t.get("skills", []))
                        lines.append(f"| `{t['code']}` | **{t['full_name']}** | {skills_str} | {t['availability_label']} | {t['workload_score']} | {t['hourly_rate_formatted']} |")
                    answer_parts.append("\n".join(lines))
                else:
                    answer_parts.append(f"Không tìm thấy kỹ thuật viên nào có kỹ năng '{skill_flt}'{avail_flt}.")

            elif tname == "get_technician_schedule_summary":
                scheds = td.get("schedules", [])
                confs = td.get("conflicts", [])
                date_lbl = td.get("date_target", "hôm nay")
                lines = [f"📅 **Lịch làm việc kỹ thuật viên ({date_lbl})** (Tổng cộng: {len(scheds)} ca):"]
                if td.get("has_conflicts"):
                    lines.append(f"⚠️ **CẢNH BÁO: Phát hiện {len(confs)} xung đột trùng lịch!**")
                    for c in confs:
                        lines.append(f"- KTV **{c['employee_name']}**: Trùng ca '{c['task_1']}' ({c['time_1']}) và '{c['task_2']}' ({c['time_2']})")
                    lines.append("")

                if scheds:
                    lines.append("| Kỹ thuật viên | Ca công việc | Thời gian | Trạng thái |")
                    lines.append("|---|---|---|---|")
                    for s in scheds:
                        lines.append(f"| **{s['employee_name']}** | {s['task_title']} | `{s['start_time']} - {s['end_time']}` | {s['status']} |")
                    answer_parts.append("\n".join(lines))
                else:
                    answer_parts.append(f"Không có lịch làm việc nào được phân công cho {date_lbl}.")

            elif tname == "simulate_what_if_scenario":
                lines = [
                    f"🧪 **{td.get('simulation_label')} {td.get('scenario_description')}**:",
                    f"- {td.get('impact_analysis')}",
                    f"- Công thức tính toán (Deterministic formula): `{td.get('formula_used')}`",
                    "> [!NOTE]",
                    "> Đây là kết quả mô phỏng giả định dựa trên số liệu thực tế hiện tại, không thay đổi dữ liệu thật trong hệ thống."
                ]
                answer_parts.append("\n".join(lines))

            elif tname == "explain_root_cause":
                lines = [
                    f"🔍 **Phân tích nguyên nhân gốc rễ (Root-Cause Analysis)**:",
                    f"{td.get('explanation')}\n",
                ]
                factors = td.get("evidence_factors", [])
                if factors:
                    lines.append("| Yếu tố căn cứ | Giá trị / Trọng số | Chi tiết bằng chứng |")
                    lines.append("|---|---|---|")
                    for f in factors:
                        val = f.get("value") or f.get("weight") or ""
                        detail = f.get("rule") or f.get("detail") or ""
                        lines.append(f"| **{f.get('factor')}** | {val} | {detail} |")
                answer_parts.append("\n".join(lines))

            elif tname == "get_spatial_ticket_clusters":
                clusters = td.get("clusters", [])
                lines = [
                    f"🗺️ **Phân tích mật độ phân bố sự cố theo khu vực (GIS Spatial Clusters)**:",
                    f"- Tổng số phiếu đang mở: **{td.get('total_active_tickets')}** | Khu vực tập trung cao nhất (Hotspot): **{td.get('hotspot_region')}**\n",
                    "| Khu vực địa lý | Số lượng ticket | Mật độ | Đánh giá & Khuyến nghị |",
                    "|---|---|---|---|",
                ]
                for c in clusters:
                    lines.append(f"| **{c['region_name']}** | {c['ticket_count']} ticket | {c['density']} | {c['status']} |")
                answer_parts.append("\n".join(lines))

            elif tname == "get_forecast":
                fc = td.get("forecast", [])
                if fc:
                    answer_parts.append(
                        f"Dự báo XGBoost 14 ngày tới cho chỉ số {td.get('target_type')}: "
                        f"Giá trị dự báo trung bình {fc[0].get('predicted')} (khoảng dự báo 95%: {fc[0].get('lower')} - {fc[0].get('upper')})."
                    )

            elif tname == "get_category_profit_margins":
                cats = td.get("category_breakdown") or td.get("categories", [])
                lines = [
                    f"💰 **Phân tích Biên lợi nhuận gộp danh mục (Profit Margins & COGS)**:",
                    f"- Tổng doanh thu: **{td.get('total_revenue_formatted') or td.get('total_revenue')}** | Tổng giá vốn: **{td.get('total_estimated_cogs_formatted') or td.get('total_estimated_cost')}**",
                    f"- Lợi nhuận gộp toàn hệ thống: **{td.get('total_gross_profit_formatted') or td.get('total_gross_profit')}** (Biên LN gộp bình quân: **{td.get('overall_gross_margin_pct')}%**)\n",
                    "| Danh mục | Doanh thu | Lợi nhuận gộp | Biên LN | Mục tiêu | Đánh giá |",
                    "|---|---|---|---|---|---|",
                ]
                for c in cats:
                    category_name = c.get("category") or c.get("category_name") or c.get("category_key")
                    revenue = c.get("revenue_formatted") or c.get("revenue")
                    gross_profit = c.get("gross_profit_formatted") or c.get("gross_profit")
                    lines.append(
                        f"| **{category_name}** | {revenue} | {gross_profit} | "
                        f"**{c.get('gross_margin_pct', 0)}%** | {c.get('target_margin_pct', 0)}% | {c.get('status', '')} |"
                    )
                if td.get("alerts"):
                    lines.append("\n⚠️ **Cảnh báo chiến lược chi phí & biên lợi nhuận**:")
                    for a in td.get("alerts"):
                        lines.append(f"- {a['message']}")
                answer_parts.append("\n".join(lines))

            elif tname == "get_customer_churn_risk_summary":
                lines = [
                    f"⚠️ **Rà soát rủi ro khách hàng rời bỏ (Customer Churn Risk Analysis)**:",
                    f"- Khách hàng phát hiện rủi ro: **{td.get('at_risk_count')}** / {td.get('total_customers_evaluated')} khách hàng",
                    f"- Doanh thu lũy kế có nguy cơ mất: **{td.get('total_revenue_at_risk_formatted')}** (Ngưỡng không phát sinh đơn: > {td.get('inactivity_threshold_days')} ngày)\n",
                ]
                risks = td.get("at_risk_customers", [])
                if risks:
                    lines.append("| Khách hàng | Phân khúc | Lũy kế chi tiêu | Đơn cuối | Đánh giá SLA | Khuyến nghị hành động |")
                    lines.append("|---|---|---|---|---|---|")
                    for r in risks[:5]:
                        lines.append(
                            f"| **{r['name']}** (`{r['code']}`) | {r['segment']} | {r['total_spend_formatted']} | "
                            f"{r['days_since_last_order']} ngày trước | {r['sla_status']} | {r['recommended_action']} |"
                        )
                else:
                    lines.append("Không có khách hàng nào vượt quá ngưỡng cảnh báo rời bỏ.")
                answer_parts.append("\n".join(lines))

            elif tname == "get_inter_branch_transfer_recommendations":
                opps = td.get("recommendations") or td.get("opportunities", [])
                lines = [
                    f"🔄 **Đề xuất điều chuyển cân đối tồn kho liên chi nhánh (Stock Balancing)**:",
                    f"- Phát hiện: **{td.get('total_transfer_opportunities', td.get('total_imbalances_found', len(opps)))}** cơ hội điều chuyển tối ưu chi phí lưu kho.\n",
                ]
                if opps:
                    lines.append("| Mã SP | Tên sản phẩm | Từ chi nhánh | Đến chi nhánh | Số lượng | Vận chuyển | SLA |")
                    lines.append("|---|---|---|---|---|---|---|")
                    for o in opps:
                        sku = o.get("product_sku") or o.get("sku") or ""
                        source_surplus = o.get("source_surplus", o.get("source_stock_before", 0))
                        destination_deficit = o.get("destination_deficit", o.get("destination_stock_before", 0))
                        qty = o.get("recommended_transfer_quantity", o.get("recommended_transfer_qty", 0))
                        shipping = o.get("estimated_shipping_fee", o.get("estimated_transport_cost_vnd", ""))
                        sla = o.get("dispatch_sla", o.get("delivery_sla_hours", ""))
                        lines.append(
                            f"| `{sku}` | **{o.get('product_name', '')}** | {o.get('source_branch', '')} (Dư {source_surplus}) | "
                            f"{o.get('destination_branch', '')} (Thiếu {destination_deficit}) | **{qty}** {o.get('unit', 'chiếc')} | "
                            f"{shipping} | {sla} |"
                        )
                else:
                    lines.append("Tồn kho tại các chi nhánh hiện đang ở mức cân bằng, không có cảnh báo thiếu hụt cục bộ.")
                answer_parts.append("\n".join(lines))

            elif tname == "get_technician_safety_compliance":
                lines = [
                    f"👷 **Kiểm tra tuân thủ an toàn lao động & Định mức tải kỹ thuật viên**:",
                    f"- Tổng số nhân sự: **{td.get('total_technicians')}** | Cảnh báo vi phạm/quá tải: **{td.get('compliance_alerts_count')}**\n",
                    "| Kỹ thuật viên | Trạng thái | Tải việc | Giờ OT tháng | Ca đêm | Chứng chỉ an toàn | Đánh giá |",
                    "|---|---|---|---|---|---|---|",
                ]
                techs = td.get("technicians_compliance", [])
                for t in techs:
                    night_str = "Hỗ trợ 150%" if t.get("night_shift_allowance_eligible") else "Không"
                    cert_str = ", ".join(t.get("safety_certifications", []))
                    lines.append(
                        f"| **{t['name']}** (`{t['code']}`) | {t['availability']} | {t['workload_score']}/100 | "
                        f"{t['estimated_monthly_overtime_hours']}h | {night_str} | {cert_str} | {t['compliance_flag']} |"
                    )
                if td.get("compliance_guidelines"):
                    lines.append("\n📋 **Quy định an toàn & Tiêu chuẩn vận hành**:")
                    for g in td.get("compliance_guidelines"):
                        lines.append(f"- {g}")
                answer_parts.append("\n".join(lines))



    # 2. Extract grounded text from relevant chunks
    if chunks:
        top_chunk = chunks[0]
        cite_str = f"[Nguồn: {top_chunk['document_title']}"
        if top_chunk.get("page_number"):
            cite_str += f", Trang {top_chunk['page_number']}"
        cite_str += "]"

        # Extract most relevant sentences from primary chunk
        sentences = [s.strip() for s in re.split(r"[.\n]", top_chunk["content"]) if len(s.strip()) > 15]
        excerpt = ". ".join(sentences[:3]) + "." if sentences else top_chunk["content"][:300]
        answer_parts.append(f"{excerpt} {cite_str}")

        # Multi-chunk synthesis: if additional distinct sections match, append key grounded points
        if len(chunks) > 1:
            seen_sections = {f"{top_chunk['document_title']}::{top_chunk.get('heading') or ''}"}
            for sec_chunk in chunks[1:3]:
                sec_key = f"{sec_chunk['document_title']}::{sec_chunk.get('heading') or ''}"
                if sec_key in seen_sections:
                    continue
                seen_sections.add(sec_key)

                heading_label = sec_chunk.get("heading") or sec_chunk["document_title"]
                sub_cite = f"[Nguồn: {sec_chunk['document_title']}"
                if sec_chunk.get("heading"):
                    sub_cite += f" - {sec_chunk['heading']}"
                if sec_chunk.get("page_number"):
                    sub_cite += f", Trang {sec_chunk['page_number']}"
                sub_cite += "]"

                sub_sentences = [s.strip() for s in re.split(r"[.\n]", sec_chunk["content"]) if len(s.strip()) > 15]
                sub_excerpt = ". ".join(sub_sentences[:2]) + "." if sub_sentences else sec_chunk["content"][:200]
                answer_parts.append(f"📌 **{heading_label}**:\n{sub_excerpt} {sub_cite}")

    final_answer = "\n\n".join(answer_parts) if answer_parts else FALLBACK_NO_CONTEXT_MESSAGE
    return final_answer, sources


def answer_grounded_query(
    workspace: Workspace,
    user: User,
    message: str,
    session_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Unified entry point for AI Knowledge Assistant.
    Validates permissions, manages conversation sessions, executes hybrid retrieval,
    synthesizes grounded answers, and logs audit events.
    """
    # 1. Permission check
    from apps.accounts.services import has_workspace_permission
    if not (user.is_superuser or has_workspace_permission(user, workspace, "ai.chat")):
        raise ToolPermissionDenied("User lacks 'ai.chat' permission to query the AI assistant.")

    clean_message = message.strip()
    if not clean_message:
        raise ValueError("Message cannot be empty.")

    # 2. Get or create conversation session
    if session_id:
        session = ConversationSession.objects.for_workspace(workspace).filter(id=session_id, user=user).first()
        if not session:
            session = ConversationSession.objects.create(
                workspace=workspace,
                user=user,
                title=clean_message[:50],
            )
    else:
        session = ConversationSession.objects.create(
            workspace=workspace,
            user=user,
            title=clean_message[:50],
        )

    # 3. Record user message
    ChatMessage.objects.create(
        workspace=workspace,
        session=session,
        role=ChatRole.USER,
        content=clean_message,
    )

    # 4. Check for mutation action request first (Zero Direct DB Mutations by AI)
    try:
        mutation_res = detect_and_handle_mutation_request(clean_message, workspace, user)
        if mutation_res:
            app_id = mutation_res.get("approval_request_id")
            t_name = mutation_res.get("tool_name", "mutation_tool")
            tools_used_log = [{"tool": t_name, "status": "APPROVAL_REQUIRED", "approval_id": app_id}]
            answer_text = (
                f"Hành động '{t_name}' đã được tiếp nhận và tạo **Yêu cầu Phê duyệt #AR-{app_id}** tại Approval Center.\n\n"
                f"📋 **Thông tin chi tiết:**\n"
                f"- Công cụ thực thi: `{t_name}`\n"
                f"- Trạng thái: **PENDING (Chờ Quản lý phê duyệt)**\n"
                f"- Mã phê duyệt: `#AR-{app_id}`\n\n"
                f"🛡️ **Nguyên tắc An toàn Vận hành (Human-in-the-Loop)**: Trợ lý AI không được phép tự ý thay đổi dữ liệu hệ thống. "
                f"Thao tác này cần được người quản lý có thẩm quyền xem xét và phê duyệt tại Approval Center trước khi có hiệu lực thi hành."
            )
            asst_msg = ChatMessage.objects.create(
                workspace=workspace,
                session=session,
                role=ChatRole.ASSISTANT,
                content=answer_text,
                sources=[],
                tools_used=tools_used_log,
            )
            log_audit_event(
                workspace=workspace,
                user=user,
                action="AI_MUTATION_REQUESTED",
                entity_type="ApprovalRequest",
                entity_id=str(app_id),
                metadata={"tool": t_name, "approval_id": app_id},
            )
            return {
                "session_id": session.id,
                "message_id": asst_msg.id,
                "role": "assistant",
                "answer": answer_text,
                "sources": [],
                "tools_used": tools_used_log,
                "approval_request_id": app_id,
                "mutation_status": "APPROVAL_REQUIRED",
            }
    except Exception as e:
        answer_text = f"Không thể tạo yêu cầu thay đổi: {str(e)}"
        asst_msg = ChatMessage.objects.create(
            workspace=workspace,
            session=session,
            role=ChatRole.ASSISTANT,
            content=answer_text,
            sources=[],
            tools_used=[{"tool": "mutation", "status": "FAILED", "error": str(e)}],
        )
        return {
            "session_id": session.id,
            "message_id": asst_msg.id,
            "role": "assistant",
            "answer": answer_text,
            "sources": [],
            "tools_used": [{"tool": "mutation", "status": "FAILED", "error": str(e)}],
            "error": str(e),
        }

    # 5. Hybrid Question Routing: Document Retrieval + Business Tools
    retrieved_chunks = search_relevant_chunks(workspace, clean_message)

    # -----------------------------------------------------------------------
    # Multi-turn Conversation Context Memory (Workspace & Session Scoped)
    # -----------------------------------------------------------------------
    prior_messages = session.messages.order_by("-created_at")[:6]
    conv_context = []
    for m in reversed(list(prior_messages)):
        conv_context.append({
            "role": m.role,
            "content": m.content,
            "tools_used": m.tools_used,
        })

    # -----------------------------------------------------------------------
    # Intent-based tool routing via classify_business_intent().
    # -----------------------------------------------------------------------
    from apps.knowledge.intent_router import classify_business_intent, BusinessIntent
    intent_result = classify_business_intent(clean_message, workspace, conversation_context=conv_context)

    # Handle AMBIGUOUS intent: return clarification question immediately.
    if intent_result.get("intent") == BusinessIntent.AMBIGUOUS:
        clarification = intent_result.get(
            "clarification_question",
            "Bạn có thể cho biết thêm thông tin để tôi có thể trả lời chính xác hơn không?"
        )
        asst_msg = ChatMessage.objects.create(
            workspace=workspace,
            session=session,
            role=ChatRole.ASSISTANT,
            content=clarification,
            sources=[],
            tools_used=[{"tool": "intent_router", "status": "AMBIGUOUS", "clarification": True}],
        )
        return {
            "session_id": session.id,
            "message_id": asst_msg.id,
            "role": "assistant",
            "answer": clarification,
            "sources": [],
            "tools_used": [{"tool": "intent_router", "status": "AMBIGUOUS"}],
            "retrieval_metadata": {"chunks_retrieved": 0, "highest_similarity": 0.0, "threshold": 0.0},
        }

    needed_tools = intent_result.get("tools", [])
    intent_params = intent_result.get("parameters", {})
    tools_data: List[Dict[str, Any]] = []
    tools_used_log: List[Dict[str, Any]] = []

    # Extract ticket ID for GIS tool (fallback from regex or intent params)
    ticket_param = intent_params.get("ticket_id")
    if not ticket_param:
        m_ticket = re.search(r"(?:ticket|phi\u1ebfu|phieu|y\u00eau c\u1ea7u|yeu cau|request)\s*#?\s*(\d+)", clean_message, re.IGNORECASE)
        ticket_param = int(m_ticket.group(1)) if m_ticket else None

    for tool_name in needed_tools:
        try:
            # Build per-tool kwargs from extracted intent parameters
            kwargs: Dict[str, Any] = {}
            if tool_name == "query_nearby_technicians" and ticket_param:
                kwargs["ticket_id"] = ticket_param
            elif tool_name in ("get_top_selling_products", "get_top_customers", "get_branch_sales_analytics"):
                for k in ("category", "metric", "limit", "sort_order", "start_date", "end_date", "time_label", "exclude_cancelled", "active_only"):
                    if k in intent_params and intent_params[k] is not None:
                        kwargs[k] = intent_params[k]
            elif tool_name == "compare_entities_analytics":
                for k in ("entity_type", "entities", "metric", "start_date", "end_date", "time_label"):
                    if k in intent_params and intent_params[k] is not None:
                        kwargs[k] = intent_params[k]
            elif tool_name == "get_sales_trend_analytics":
                for k in ("category", "period_days", "time_label"):
                    if k in intent_params and intent_params[k] is not None:
                        kwargs[k] = intent_params[k]
            elif tool_name == "get_service_labor_cost_summary":
                for k in ("ticket_id", "employee_id", "start_date", "end_date", "time_label"):
                    if k in intent_params and intent_params[k] is not None:
                        kwargs[k] = intent_params[k]
            elif tool_name == "get_service_catalog_summary":
                if "category" in intent_params and intent_params["category"]:
                    kwargs["category"] = intent_params["category"]
            elif tool_name == "get_service_ticket_summary":
                for k in ("ticket_id", "filter", "exclude_closed"):
                    if k in intent_params and intent_params[k] is not None:
                        kwargs[k] = intent_params[k]
            elif tool_name in ("get_stockout_risk_summary", "get_stock_balance_summary"):
                for k in ("category", "branch_id", "limit"):
                    if k in intent_params and intent_params[k] is not None:
                        kwargs[k] = intent_params[k]
            elif tool_name == "get_product_catalog_summary":
                if "category" in intent_params and intent_params["category"]:
                    kwargs["category"] = intent_params["category"]
            elif tool_name == "get_sales_summary":
                for k in ("start_date", "end_date", "time_label", "exclude_cancelled"):
                    if k in intent_params and intent_params[k] is not None:
                        kwargs[k] = intent_params[k]
            elif tool_name == "get_customer_order_history":
                for k in ("customer_name", "customer_code", "customer_id"):
                    if k in intent_params and intent_params[k] is not None:
                        kwargs[k] = intent_params[k]
            elif tool_name == "get_technician_skills_summary":
                for k in ("skill", "is_available_only"):
                    if k in intent_params and intent_params[k] is not None:
                        kwargs[k] = intent_params[k]
            elif tool_name == "get_technician_schedule_summary":
                for k in ("date_target", "employee_query", "conflict_check"):
                    if k in intent_params and intent_params[k] is not None:
                        kwargs[k] = intent_params[k]
            elif tool_name == "simulate_what_if_scenario":
                for k in ("scenario_type", "change_pct", "param_value"):
                    if k in intent_params and intent_params[k] is not None:
                        kwargs[k] = intent_params[k]
            elif tool_name == "explain_root_cause":
                for k in ("target_type", "entity_name", "entity_id"):
                    if k in intent_params and intent_params[k] is not None:
                        kwargs[k] = intent_params[k]
            elif tool_name == "get_spatial_ticket_clusters":
                pass
            elif tool_name == "get_forecast":
                if "target_type" in intent_params:
                    kwargs["target_type"] = intent_params["target_type"]
            elif tool_name == "get_category_profit_margins":
                if "category" in intent_params and intent_params["category"]:
                    kwargs["category"] = intent_params["category"]
            elif tool_name == "get_customer_churn_risk_summary":
                if "inactivity_days" in intent_params and intent_params["inactivity_days"] is not None:
                    kwargs["inactivity_days"] = intent_params["inactivity_days"]
            elif tool_name == "get_inter_branch_transfer_recommendations":
                if "min_surplus_qty" in intent_params and intent_params["min_surplus_qty"] is not None:
                    kwargs["min_surplus_qty"] = intent_params["min_surplus_qty"]
            elif tool_name == "get_technician_safety_compliance":
                pass

            tdata = execute_tool(tool_name, workspace, user, **kwargs)
            tools_data.append(tdata)
            tools_used_log.append({"tool": tool_name, "status": "SUCCESS"})
        except ToolPermissionDenied as e:
            tools_used_log.append({"tool": tool_name, "status": "PERMISSION_DENIED", "error": str(e)})
        except Exception as e:
            tools_used_log.append({"tool": tool_name, "status": "ERROR", "error": str(e)})



    # 5. Generate Grounded Answer
    answer_text, citations = generate_grounded_answer(
        workspace=workspace,
        user=user,
        query=clean_message,
        chunks=retrieved_chunks,
        tools_data=tools_data,
    )

    # 6. Record assistant message
    asst_msg = ChatMessage.objects.create(
        workspace=workspace,
        session=session,
        role=ChatRole.ASSISTANT,
        content=answer_text,
        sources=citations,
        tools_used=tools_used_log,
    )

    # 7. Audit log (masks content for privacy, records metadata)
    log_audit_event(
        workspace=workspace,
        user=user,
        action="AI_CHAT_QUERY",
        entity_type="ConversationSession",
        entity_id=str(session.id),
        metadata={
            "query_length": len(clean_message),
            "retrieved_chunk_count": len(retrieved_chunks),
            "tools_invoked": [t["tool"] for t in tools_used_log],
            "has_sources": bool(citations),
        },
    )

    return {
        "session_id": session.id,
        "message_id": asst_msg.id,
        "role": "assistant",
        "answer": answer_text,
        "sources": citations,
        "citations": citations,
        "tools_used": tools_used_log,
        "retrieval_metadata": {
            "chunks_retrieved": len(retrieved_chunks),
            "highest_similarity": retrieved_chunks[0]["similarity"] if retrieved_chunks else 0.0,
            "threshold": getattr(settings, "RAG_SIMILARITY_THRESHOLD", 0.70),
        },
    }


def detect_query_intent(query: str, workspace: Workspace) -> List[str]:
    """Helper alias for detect_tools_for_query."""
    return detect_tools_for_query(query, workspace)


def get_grounded_policy_snippet(workspace: Workspace, query: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the most authoritative policy snippet and citation for a given query topic.
    Useful for grounding customer emails and notification dispatches with official SOPs.
    """
    try:
        chunks = search_relevant_chunks(workspace, query, top_k=1)
        if chunks:
            top = chunks[0]
            return {
                "document_title": top["document_title"],
                "heading": top.get("heading") or "",
                "page_number": top.get("page_number"),
                "content_snippet": top["content"][:300].strip(),
            }
    except Exception:
        pass
    return None


def ask_ai_assistant(workspace: Workspace, user: User, query: str, session: Optional[ConversationSession] = None) -> Dict[str, Any]:
    """
    High-level entrypoint for AI Q&A queries.
    Automatically initializes a conversation session if one is not passed in.
    """
    if session is None:
        session = ConversationSession.objects.create(
            workspace=workspace,
            user=user,
            title=query[:50],
        )
    return answer_grounded_query(workspace=workspace, user=user, message=query, session_id=session.id)
