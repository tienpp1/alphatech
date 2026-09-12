"""
Deterministic Vietnamese Business Intent Parser & Tool Dispatcher for AI Assistant.
Enforces multi-layer semantic normalization, entity extraction, ranking, date resolution,
ambiguity detection, comparison, trend analysis, negation filtering, conversation context resolution,
and permission-guarded tool dispatching across Retail, Service, GIS, and Policy domains.
"""

import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from django.utils import timezone

from apps.workspaces.models import Workspace


def strip_accents_and_lower(text: str) -> str:
    """Normalizes Vietnamese text by removing diacritics and converting to lowercase."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accent = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accent.replace("đ", "d").replace("Đ", "d").lower().strip()


def parse_date_range_from_text(query: str, reference_date: Optional[date] = None) -> Tuple[Optional[date], Optional[date], str]:
    """
    Parses Vietnamese relative temporal phrases into deterministic date bounds [start_date, end_date].
    Returns (start_date, end_date, time_label).
    """
    today = reference_date or timezone.now().date()
    norm = strip_accents_and_lower(query)

    # Specific phrase match
    if "hom nay" in norm:
        return today, today, "hôm nay"
    if "hom qua" in norm:
        yest = today - timedelta(days=1)
        return yest, yest, "hôm qua"
    if "tuan nay" in norm:
        start = today - timedelta(days=today.weekday())
        return start, today, "tuần này"
    if "tuan truoc" in norm:
        end = today - timedelta(days=today.weekday() + 1)
        start = end - timedelta(days=6)
        return start, end, "tuần trước"
    if "thang nay" in norm:
        start = date(today.year, today.month, 1)
        return start, today, "tháng này"
    if "thang truoc" in norm:
        first_this = date(today.year, today.month, 1)
        last_prev = first_this - timedelta(days=1)
        start = date(last_prev.year, last_prev.month, 1)
        return start, last_prev, "tháng trước"
    if "quy nay" in norm:
        quarter = (today.month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        start = date(today.year, start_month, 1)
        return start, today, "quý này"
    if "nam nay" in norm:
        start = date(today.year, 1, 1)
        return start, today, "năm nay"

    m_days = re.search(r"(\d+)\s*ngay\s*(?:qua|gan day|vua qua)", norm)
    if m_days:
        days = int(m_days.group(1))
        return today - timedelta(days=days), today, f"{days} ngày qua"

    m_months = re.search(r"(\d+)\s*thang\s*(?:qua|gan day|vua qua)", norm)
    if m_months:
        months = int(m_months.group(1))
        return today - timedelta(days=months * 30), today, f"{months} tháng gần đây"

    return None, None, "toàn thời gian"


def extract_limit_and_ordering(query: str) -> Tuple[int, str]:
    """
    Extracts limit and sorting direction from query.
    Returns (limit, sort_order) where sort_order in ('DESC', 'ASC').
    """
    norm = strip_accents_and_lower(query)
    
    # Check top N
    m_top = re.search(r"\btop\s*(\d+)\b", norm)
    if m_top:
        limit = int(m_top.group(1))
    else:
        # Check single top / lowest
        if any(k in norm for k in ["nhat", "top 1", "dau bang", "cao nhat", "thap nhat", "it nhat", "nhieu nhat", "dung dau", "dung cuoi", "kem nhat"]):
            limit = 1
        else:
            limit = 5

    # Determine sort order (ascending vs descending)
    if any(k in norm for k in ["thap nhat", "it nhat", "kem nhat", "giam manh nhat", "e am nhat", "e nhat", "ban cham nhat", "dung cuoi", "ranh nhat", "it viec nhat"]):
        sort_order = "ASC"
    else:
        sort_order = "DESC"

    return limit, sort_order


def extract_product_category(query: str) -> Optional[str]:
    """
    Extracts canonical category keywords from query.
    """
    norm = strip_accents_and_lower(query)
    cat_mapping = {
        "laptop": ["laptop", "may tinh xach tay", "macbook", "zenbook", "thinkpad", "vivobook", "ideapad", "vostro", "asus", "lenovo", "dell"],
        "smartphone": ["smartphone", "dien thoai", "phone", "iphone", "galaxy", "di dong", "samsung"],
        "mouse": ["chuot", "mouse", "logitech mouse"],
        "keyboard": ["ban phim", "keyboard", "keychron", "ban phim co"],
        "headset": ["tai nghe", "headset", "headphone", "airpods"],
        "webcam": ["webcam", "camera hoi nghi"],
        "components": ["linh kien", "cpu", "ram", "o cung", "ssd", "vga", "mainboard", "kingston"],
        "networking": ["thiet bi mang", "networking", "router", "switch", "wifi", "modem", "tp-link", "tplink"],
    }
    for cat_code, synonyms in cat_mapping.items():
        for syn in synonyms:
            pattern = r"(?:\b|\s|^)" + re.escape(syn) + r"(?:\b|\s|$)"
            if re.search(pattern, norm):
                return cat_code
    return None


def extract_comparison_entities(query: str) -> Tuple[str, List[str]]:
    """
    Extracts compared entities and type (product vs branch) from comparison questions.
    Returns (entity_type, [entity_a, entity_b]).
    """
    norm = strip_accents_and_lower(query)
    raw = query

    # 1. Branch comparison
    if "chi nhanh" in norm or "cua hang" in norm or "co so" in norm:
        # e.g., "Chi nhánh Quận 1 so với Chi nhánh Quận 3", "cửa hàng A và B"
        m_branches = re.findall(r"(?:chi\s*nhanh|cua\s*hang|co\s*so)\s*([A-Za-z0-9\s_]+?)(?=\s*(?:so\s*voi|va|hay|hon|ve|,|\?|$))", raw, re.IGNORECASE)
        clean = [b.strip() for b in m_branches if len(b.strip()) > 0 and b.lower() not in ["nao", "gi"]]
        if len(clean) >= 2:
            return "branch", clean[:2]
        elif len(clean) == 1:
            m_second = re.search(r"(?:so\s*voi|va|hay)\s*(?:chi\s*nhanh|cua\s*hang|co\s*so)?\s*([A-Za-z0-9\s_]+?)(?=\s*(?:ve|hon|,|\?|$))", raw, re.IGNORECASE)
            if m_second and m_second.group(1).strip():
                clean.append(m_second.group(1).strip())
                return "branch", clean[:2]
        return "branch", clean

    # 2. Known brand/product comparison (ASUS vs Lenovo, VivoBook vs IdeaPad, Mouse vs Keyboard, MacBook vs ThinkPad)
    known_brands = [
        "asus", "lenovo", "dell", "logitech", "kingston", "tp-link", "apple", "samsung",
        "vivobook", "ideapad", "vostro", "macbook", "thinkpad", "g pro", "chuot", "ban phim", "tai nghe"
    ]

    found_brands = []
    for b in known_brands:
        if re.search(r"(?:\b|\s|^)" + re.escape(b) + r"(?:\b|\s|$)", norm):
            found_brands.append(b.upper())
    if len(found_brands) >= 2:
        return "product", found_brands[:2]

    # 3. Generic "X và Y cái nào..." or "X hay Y bán tốt hơn"
    m_pair = re.search(r"([A-Za-z0-9\s_-]+?)\s+(?:va|hay|so\s*voi)\s+([A-Za-z0-9\s_-]+?)\s+(?:cai\s*nao|ben\s*nao|san\s*pham\s*nao|ban\s*chay|tot\s*hon|doanh\s*thu|cao\s*hon)", raw, re.IGNORECASE)
    if m_pair:
        ent1 = m_pair.group(1).strip()
        ent2 = m_pair.group(2).strip()
        if len(ent1) > 1 and len(ent2) > 1:
            return "product", [ent1, ent2]

    return "product", []


def extract_negations_and_exclusions(query: str) -> Dict[str, bool]:
    """
    Extracts explicit negative or exclusion conditions in Vietnamese business queries.
    """
    norm = strip_accents_and_lower(query)
    exclude_cancelled = bool(re.search(r"(?:khong\s*tinh|bo\s*qua|loai\s*tru|tru)\s*(?:don\s*hang\s*)?(?:da\s*)?(?:huy|cancelled)", norm))
    active_only = bool(re.search(r"(?:bo\s*qua|khong\s*tinh|loai\s*tru)\s*(?:san\s*pham\s*)?(?:ngung\s*kinh\s*doanh|ngung\s*ban|inactive)", norm))
    exclude_closed = bool(re.search(r"(?:khong\s*tinh|bo\s*qua|loai\s*tru)\s*(?:ticket|phieu\s*yeu\s*cau)?\s*(?:da\s*)?(?:dong|closed|giai\s*quyet)", norm))
    completed_only = bool(re.search(r"(?:chi\s*tinh|chi\s*lay)\s*(?:don\s*)?(?:hoan\s*thanh|completed)", norm))

    return {
        "exclude_cancelled": exclude_cancelled or completed_only or True,
        "active_only": active_only,
        "exclude_closed": exclude_closed,
    }


def extract_branch_name(query: str) -> Optional[str]:
    """Extracts branch name or district mention from query."""
    norm = strip_accents_and_lower(query)
    raw = query
    m_br = re.search(r"(?:chi\s*nhanh|cua\s*hang|co\s*so)\s*([A-Za-z0-9\s_]+?)(?=\s*(?:trong|thang|nam|tuan|ngay|ban|co|doanh|la|,|\?|$))", raw, re.IGNORECASE)
    if m_br and m_br.group(1).strip() and m_br.group(1).lower() not in ["nao", "gi", "tot", "thap"]:
        return m_br.group(1).strip()
    # Check known branches
    for b in ["tan phu", "quan 1", "quan 3", "quan 7", "binh thanh", "thu duc"]:
        if b in norm:
            return b.title()
    return None


def extract_customer_name(query: str) -> Optional[str]:
    """Extracts customer name or identifier from query."""
    norm = strip_accents_and_lower(query)
    m_cust = re.search(r"(?:khach\s*hang|khach)\s+([A-Za-z0-9\s_]+?)(?=\s*(?:da\s*mua|tung\s*mua|mua\s*gi|la\s*ai|o\s*dau|co|,|\?|$))", norm, re.IGNORECASE)
    if m_cust and m_cust.group(1).strip() and m_cust.group(1).lower() not in ["nao", "gi", "hang", "mua"]:
        return m_cust.group(1).strip().upper()
    return None


def extract_skill_keyword(query: str) -> Optional[str]:
    """Extracts technician technical skills from query."""
    norm = strip_accents_and_lower(query)
    skills_map = {
        "DATABASE": ["database", "csdl", "co so du lieu", "sql"],
        "POSTGRESQL": ["postgresql", "postgres", "pg"],
        "SERVER": ["server", "may chu", "he thong chu"],
        "NETWORK": ["network", "ha tang mang", "thiet bi mang", "quan tri mang", "he thong mang"],
        "WINDOWS": ["windows", "win 10", "win 11", "win server"],
        "LINUX": ["linux", "ubuntu", "centos", "redhat"],
        "LAPTOP_REPAIR": ["laptop repair", "sua laptop", "phan cung laptop"],
        "DESKTOP_REPAIR": ["desktop repair", "sua may ban", "sua desktop"],
        "PRINTER": ["printer", "may in", "sua may in"],
    }
    for sk, syns in skills_map.items():
        for syn in syns:
            if re.search(r"(?:\b|\s|^)" + re.escape(syn) + r"(?:\b|\s|$)", norm):
                return sk
    return None



class BusinessIntent:
    CATALOG_COUNT = "CATALOG_COUNT"
    CATALOG_LIST = "CATALOG_LIST"
    TOP_SELLING_PRODUCTS = "TOP_SELLING_PRODUCTS"
    TOP_REVENUE_PRODUCTS = "TOP_REVENUE_PRODUCTS"
    PRODUCT_PERFORMANCE = "PRODUCT_PERFORMANCE"
    TOP_CUSTOMERS = "TOP_CUSTOMERS"
    CUSTOMER_SUMMARY = "CUSTOMER_SUMMARY"
    CUSTOMER_ORDER_HISTORY = "CUSTOMER_ORDER_HISTORY"
    BRANCH_REVENUE = "BRANCH_REVENUE"
    SALES_SUMMARY = "SALES_SUMMARY"
    SALES_TREND = "SALES_TREND"
    COMPARISON = "COMPARISON"
    FORECAST_METRICS = "FORECAST_METRICS"
    STOCKOUT_RISK = "STOCKOUT_RISK"
    STOCK_BALANCE = "STOCK_BALANCE"
    SERVICE_TICKETS_SUMMARY = "SERVICE_TICKETS_SUMMARY"
    SERVICE_SLA_AT_RISK = "SERVICE_SLA_AT_RISK"
    TICKET_LOOKUP = "TICKET_LOOKUP"
    SERVICE_LABOR_COST = "SERVICE_LABOR_COST"
    SERVICE_CATALOG = "SERVICE_CATALOG"
    TECHNICIAN_WORKLOAD = "TECHNICIAN_WORKLOAD"
    TECHNICIAN_NEARBY_GIS = "TECHNICIAN_NEARBY_GIS"
    TECHNICIAN_RECOMMENDATION = "TECHNICIAN_RECOMMENDATION"
    TECHNICIAN_SKILLS = "TECHNICIAN_SKILLS"
    TECHNICIAN_SCHEDULE = "TECHNICIAN_SCHEDULE"
    WHAT_IF_SIMULATION = "WHAT_IF_SIMULATION"
    ROOT_CAUSE_EXPLANATION = "ROOT_CAUSE_EXPLANATION"
    GIS_TICKET_CLUSTERING = "GIS_TICKET_CLUSTERING"
    PROFIT_MARGIN_ANALYSIS = "PROFIT_MARGIN_ANALYSIS"
    CUSTOMER_CHURN_RISK = "CUSTOMER_CHURN_RISK"
    INTER_BRANCH_TRANSFER = "INTER_BRANCH_TRANSFER"
    TECHNICIAN_COMPLIANCE = "TECHNICIAN_COMPLIANCE"
    RECOMMENDATIONS = "RECOMMENDATIONS"
    RMA_WARRANTY_PROTOCOL = "RMA_WARRANTY_PROTOCOL"
    SUPPLIER_CONTRACT_PENALTIES = "SUPPLIER_CONTRACT_PENALTIES"
    OMNICHANNEL_FULFILLMENT = "OMNICHANNEL_FULFILLMENT"
    CYBERSECURITY_INCIDENT_DRP = "CYBERSECURITY_INCIDENT_DRP"
    SLA_ESCALATION_MATRIX = "SLA_ESCALATION_MATRIX"
    DATACENTER_ENVIRONMENT = "DATACENTER_ENVIRONMENT"
    PROMOTION_FRAUD_CONTROL = "PROMOTION_FRAUD_CONTROL"
    INVENTORY_AUDIT_DISPOSAL = "INVENTORY_AUDIT_DISPOSAL"
    TRADE_IN_DATA_SECURITY = "TRADE_IN_DATA_SECURITY"
    ITIL_CHANGE_MANAGEMENT = "ITIL_CHANGE_MANAGEMENT"
    DATA_SANITIZATION_NIST = "DATA_SANITIZATION_NIST"
    BACKUP_DISASTER_RECOVERY_DRILL = "BACKUP_DISASTER_RECOVERY_DRILL"
    CORE_WORKING_HOURS_LEAVE = "CORE_WORKING_HOURS_LEAVE"
    CORE_EXPENSE_TRAVEL_REIMBURSEMENT = "CORE_EXPENSE_TRAVEL_REIMBURSEMENT"
    CORE_IT_SECURITY_DEVICE_USAGE = "CORE_IT_SECURITY_DEVICE_USAGE"
    CORE_ONBOARDING_PROBATION = "CORE_ONBOARDING_PROBATION"
    CORE_CODE_OF_CONDUCT_CULTURE = "CORE_CODE_OF_CONDUCT_CULTURE"
    CORE_PERFORMANCE_BENEFITS_BONUS = "CORE_PERFORMANCE_BENEFITS_BONUS"
    DOCUMENT_RAG = "DOCUMENT_RAG"
    MUTATION_ACTION = "MUTATION_ACTION"
    AMBIGUOUS = "AMBIGUOUS"



def _contains_word_or_phrase(text: str, phrases: List[str]) -> bool:
    """
    Checks if text contains any phrase using regex word boundaries to prevent
    partial substring matches.
    """
    for p in phrases:
        pattern = r"(?:\b|\s|^)" + re.escape(p) + r"(?:\b|\s|$)"
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def resolve_follow_up_context(
    query: str,
    conversation_context: Optional[List[Dict[str, Any]]] = None,
    workspace: Optional[Workspace] = None,
) -> Dict[str, Any]:
    """
    Resolves conversational follow-up references (e.g. 'Còn ASUS thì sao?', 'Tháng trước thì thế nào?',
    'Cái đó còn hàng không?', 'Chi phí là bao nhiêu?', 'Vậy ai xử lý được?')
    by carrying forward entities, category, branch, ticket, or intent from recent turns safely.
    """
    if not conversation_context:
        return {}

    norm = strip_accents_and_lower(query)
    inherited: Dict[str, Any] = {}

    last_turn = conversation_context[-1] if conversation_context else {}
    last_intent = last_turn.get("intent")
    last_params = last_turn.get("parameters", {})

    # 1. "Còn ASUS / Lenovo / iPhone thì sao?"
    m_entity = re.search(r"con\s+([A-Za-z0-9\s_-]+?)\s+(?:thi\s*sao|the\s*nao)", norm)
    if m_entity:
        new_ent = m_entity.group(1).strip()
        inherited["category"] = extract_product_category(new_ent) or last_params.get("category")
        inherited["entity_name"] = new_ent
        inherited["inherited_intent"] = last_intent or BusinessIntent.TOP_SELLING_PRODUCTS
        inherited["tools"] = ["get_top_selling_products"]
        inherited["parameters"] = {
            "category": inherited["category"],
            "metric": last_params.get("metric", "quantity_sold"),
            "limit": last_params.get("limit", 1),
            "time_label": last_params.get("time_label", "tháng này"),
        }
        return inherited

    # 2. "Tháng trước thì thế nào?" / "Còn tuần này?"
    if any(k in norm for k in ["thang truoc", "thang nay", "tuan nay", "tuan truoc", "hom qua", "quy nay", "nam nay"]):
        s_date, e_date, t_label = parse_date_range_from_text(query)
        inherited["inherited_intent"] = last_intent or BusinessIntent.SALES_SUMMARY
        inherited["category"] = last_params.get("category")
        inherited["branch"] = last_params.get("branch")
        inherited["tools"] = ["get_sales_summary"]
        inherited["parameters"] = {
            "start_date": s_date,
            "end_date": e_date,
            "time_label": t_label,
            "category": last_params.get("category"),
        }
        return inherited

    # 3. "Cái đó còn hàng không?" / "Còn bao nhiêu cái?"
    if _contains_word_or_phrase(norm, ["cai do con hang", "con bao nhieu cai", "con hang khong", "con trong kho", "cai do"]):
        inherited["inherited_intent"] = BusinessIntent.STOCK_BALANCE
        inherited["category"] = last_params.get("category")
        inherited["tools"] = ["get_stock_balance_summary"]
        inherited["parameters"] = {
            "category": last_params.get("category"),
            "limit": 5,
        }
        return inherited

    # 4. "Vậy ai xử lý được?" / "Ai phù hợp?"
    if _contains_word_or_phrase(norm, ["ai xu ly duoc", "ai phu hop", "ai nen lam", "ai gan nhat", "vay ai"]):
        inherited["inherited_intent"] = BusinessIntent.TECHNICIAN_NEARBY_GIS if "gan" in norm else BusinessIntent.TECHNICIAN_RECOMMENDATION
        inherited["ticket_id"] = last_params.get("ticket_id")
        inherited["tools"] = ["query_nearby_technicians"] if "gan" in norm else ["get_recommendations", "get_technician_workload_summary"]
        inherited["parameters"] = {
            "ticket_id": last_params.get("ticket_id"),
        }
        return inherited

    # 5. "Chi phí là bao nhiêu?" / "Tiền công thế nào?"
    if _contains_word_or_phrase(norm, ["chi phi la bao nhieu", "tien cong the nao", "ton bao nhieu gio", "chi phi"]):
        inherited["inherited_intent"] = BusinessIntent.SERVICE_LABOR_COST
        inherited["ticket_id"] = last_params.get("ticket_id")
        inherited["tools"] = ["get_service_labor_cost_summary"]
        inherited["parameters"] = {
            "ticket_id": last_params.get("ticket_id"),
        }
        return inherited

    return inherited


def classify_business_intent(
    query: str,
    workspace: Workspace,
    conversation_context: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Deterministically extracts intent, entities, metrics, parameters, exclusions,
    and suggested tools across Retail, Service, GIS, Forecasting, and Knowledge domains.
    """
    norm = strip_accents_and_lower(query)
    ws_type = getattr(workspace, "workspace_type", "RETAIL")
    start_date, end_date, time_label = parse_date_range_from_text(query)
    limit, sort_order = extract_limit_and_ordering(query)
    category = extract_product_category(query)
    exclusions = extract_negations_and_exclusions(query)

    # 0. Conversational Follow-up Resolution
    follow_up = resolve_follow_up_context(query, conversation_context, workspace)
    if follow_up and follow_up.get("inherited_intent"):
        return {
            "intent": follow_up["inherited_intent"],
            "tools": follow_up.get("tools", []),
            "parameters": follow_up.get("parameters", {}),
        }

    # 1. Genuine Ambiguity Detection
    # Queries like "Laptop nào tốt nhất?" without specifying a metric
    if re.search(r"\b(?:tot nhat|hay nhat|vip nhat|ok nhat|on nhat|dinh nhat)\b", norm):
        has_concrete_metric = _contains_word_or_phrase(norm, [
            "ban chay", "doanh thu", "doanh so", "so luong", "don hang", "gia",
            "khach hang", "khach", "ky thuat", "luong ban", "gia tien", "bao hanh"
        ])
        if not has_concrete_metric:
            return {
                "intent": BusinessIntent.AMBIGUOUS,
                "clarification_question": "Bạn muốn đánh giá theo doanh số bán ra (số lượng chiếc), doanh thu mang lại (VND) hay tiêu chí kỹ thuật cụ thể nào?",
                "tools": [],
                "parameters": {},
            }

    # Domain-specific analytics take precedence over generic comparison,
    # technician-workload and mutation keyword matches.  This keeps read-only
    # questions such as "đề xuất điều chuyển..." out of the approval path,
    # while explicit create/lập actions remain mutations below.
    has_explicit_mutation = _contains_word_or_phrase(norm, [
        "tao de xuat", "lap de xuat", "tao phieu", "tao nhiem vu",
        "cap nhat", "dieu chinh gia", "ha gia", "giam gia", "xa kho",
        "de xuat doi moi", "lap de xuat doi moi", "de xuat phat", "lap de xuat phat",
        "de xuat chi vien", "lap de xuat chi vien",
    ])
    if _contains_word_or_phrase(norm, [
        "neu", "gia dinh", "mo phong", "gia su",
    ]) and _contains_word_or_phrase(norm, [
        "gia von", "bien loi nhuan", "loi nhuan", "chi phi",
    ]):
        return {
            "intent": BusinessIntent.WHAT_IF_SIMULATION,
            "tools": ["simulate_what_if_scenario"],
            "parameters": {"scenario_type": "COST_CHANGE", "change_pct": 10.0},
        }

    if _contains_word_or_phrase(norm, [
        "bien loi nhuan", "ty suat loi nhuan", "loi nhuan gop", "margin",
        "gia von", "loi nhuan danh muc",
    ]) and not _contains_word_or_phrase(norm, ["neu", "gia dinh", "mo phong", "gia su"]):
        return {
            "intent": BusinessIntent.PROFIT_MARGIN_ANALYSIS,
            "tools": ["get_category_profit_margins"],
            "parameters": {"category": category},
        }

    if _contains_word_or_phrase(norm, [
        "dieu chuyen ton kho", "can doi ton kho", "chuyen hang giua",
        "thieu hut tai", "chuyen giua cac chi nhanh", "dieu chuyen noi bo",
        "de xuat dieu chuyen",
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.INTER_BRANCH_TRANSFER,
            "tools": ["get_inter_branch_transfer_recommendations"],
            "parameters": {},
        }

    if _contains_word_or_phrase(norm, [
        "gio lam them", "overtime", "lam them gio", "an toan lao dong",
        "phu cap ca dem", "iso 27001", "chung chi ky thuat", "an toan dien",
    ]):
        return {
            "intent": BusinessIntent.TECHNICIAN_COMPLIANCE,
            "tools": ["get_technician_safety_compliance"],
            "parameters": {},
        }

    # 1b. New Phase 3 Enterprise SOP Intents (RMA, Supplier Penalties, Omnichannel, DRP, Escalation, Datacenter)
    if _contains_word_or_phrase(norm, [
        "doa", "dead on arrival", "doi moi trong 72 gio", "doi moi 72h", "72 gio doi moi", "72h doi moi",
        "loi trong 72 gio", "loi trong 72h", "trong 72 gio", "trong 72h",
        "loi ban dau", "diem chet", "diem sang", "rma", "bao hanh hang", "gui hang bao hanh",
        "tem void", "tem niem phong", "loi do nguoi dung", "vao nuoc", "roi vo",
        "tro gia sua chua", "tro gia 30%", "cid", "muon may", "cho muon may",
        "may tinh thay the", "loaner pc", "loaner", "chinh sach rma"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.RMA_WARRANTY_PROTOCOL,
            "tools": [],
            "parameters": {"policy_topic": "RMA_WARRANTY"},
        }

    if _contains_word_or_phrase(norm, [
        "phat giao tre", "phat tre han", "giao hang cham", "phat nha cung cap",
        "che tai phat", "0.5%", "tran 8%", "huy po", "tre qua 10 ngay",
        "aql", "aql 2.0%", "mil-std-105e", "tu choi ca lo", "tu choi lo hang",
        "thu hoi lo hang", "batch rejection", "lo hang loi", "bao ho gia",
        "price protection", "credit note", "bu chenh lech gia", "hop dong nha cung cap"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.SUPPLIER_CONTRACT_PENALTIES,
            "tools": [],
            "parameters": {"policy_topic": "SUPPLIER_PENALTIES"},
        }

    if _contains_word_or_phrase(norm, [
        "bopis", "mua online nhan tai cua hang", "nhan tai cua hang", "chuan bi hang 30 phut",
        "giu hang 48 gio", "giu hang 48h", "huy lenh giu hang", "hoan kho bopis",
        "dong goi cong nghe", "dong goi de vo", "xop bong khi", "3 lop xop",
        "bang keo an ninh", "tamper evident", "quay video dong hang", "video dong hang",
        "video tren 5 trieu", "don hang tren 5 trieu", "video 5 trieu", "omnichannel"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.OMNICHANNEL_FULFILLMENT,
            "tools": [],
            "parameters": {"policy_topic": "OMNICHANNEL"},
        }

    # Backup 3-2-1-1 & Recovery Drill (Evaluated before general DRP to catch backup-specific queries)
    if _contains_word_or_phrase(norm, [
        "3-2-1-1", "sao luu 3-2-1", "sao luu 3-2-1-1", "immutable storage", "worm", "write once read many",
        "object lock", "offsite backup", "cach xa 50km", "incremental snapshot", "hourly backup",
        "differential backup", "retention policy", "vong doi luu tru", "dien tap phuc hoi",
        "recovery drill", "monthly recovery drill", "sandbox phuc hoi"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.BACKUP_DISASTER_RECOVERY_DRILL,
            "tools": [],
            "parameters": {"policy_topic": "BACKUP_RETENTION"},
        }

    if _contains_word_or_phrase(norm, [
        "ransomware", "ma doc tong tien", "ddos", "10gbps", "su co p0", "an ninh mang",
        "ro ri du lieu", "data exfiltration", "co lap mang", "co lap mang 5 phut",
        "ngat vlan", "ngat switch", "no reboot", "khong khoi dong lai", "tuyet doi khong reboot",
        "bao ton ram", "digital forensics", "phap y so", "rto", "rpo", "rto 4 gio",
        "rpo 1 gio", "phuc hoi tham hoa", "drp", "air-gapped", "rca 48 gio", "bao cao rca"
    ]) and not _contains_word_or_phrase(norm, ["3-2-1-1", "sao luu", "worm", "dien tap", "recovery drill"]):
        return {
            "intent": BusinessIntent.CYBERSECURITY_INCIDENT_DRP,
            "tools": [],
            "parameters": {"policy_topic": "CYBERSECURITY"},
        }

    if _contains_word_or_phrase(norm, [
        "leo thang sla", "escalation", "tier 1", "tier 2", "tier 3", "50% sla", "75% sla",
        "100% sla", "canh bao leo thang", "chi vien hien truong", "dieu dong chi vien",
        "bao dong do", "tranh chap ky thuat", "hoa giai tranh chap", "hoi dong tham dinh",
        "bien ban lien tich", "do fluke", "kiem tra lai hien truong", "leo thang",
        "ma tran leo thang", "50%", "75%", "100%", "leo thang su co"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.SLA_ESCALATION_MATRIX,
            "tools": [],
            "parameters": {"policy_topic": "SLA_ESCALATION"},
        }

    if _contains_word_or_phrase(norm, [
        "hanh lang lanh", "cold aisle", "nhiet do phong server", "18 den 24", "18-24",
        "ashrae", "do am 45", "canh bao 27", "bao dong 30", "ngat dien khan cap", "epo",
        "35 do", "nguon dien n+1", "nguon a nguon b", "dual feed", "may phat dien diesel",
        "ats", "15 giay", "hoa dien 15s", "72 gio chay", "dien tap cup dien", "blackout drill"
    ]):
        return {
            "intent": BusinessIntent.DATACENTER_ENVIRONMENT,
            "tools": [],
            "parameters": {"policy_topic": "DATACENTER"},
        }

    # 1c. Phase 4 Enterprise SOP Intents (Promo Fraud, Inventory Audit & Disposal, Trade-In & Data Security, ITIL CAB, NIST 800-88 Decommission, Backup 3-2-1-1)
    if _contains_word_or_phrase(norm, [
        "fraud hold", "gian lan khuyen mai", "lam dung voucher", "lam dung ma giam gia", "clone tai khoan",
        "voucher new user", "staff discount", "chiet khau nhan vien", "uu dai nhan vien",
        "90-day retention", "giu may 90 ngay", "kich hoat 90 ngay", "giai toa fraud hold",
        "dau co voucher", "dau co ma", "gom don"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.PROMOTION_FRAUD_CONTROL,
            "tools": [],
            "parameters": {"policy_topic": "PROMO_FRAUD"},
        }

    if _contains_word_or_phrase(norm, [
        "cycle count", "kiem ke cuon chieu", "kiem ke kho", "kiem ke hang tuan",
        "hang gia tri cao", "zero tolerance", "wall-to-wall", "kiem ke toan dien",
        "that thoat kho", "0.2% doanh so", "niem phong camera", "pin phong", "pin chai phong",
        "pin lithium", "thung kim loai chong chay", "cat kho", "tieu huy pin", "chat thai nguy hai"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.INVENTORY_AUDIT_DISPOSAL,
            "tools": [],
            "parameters": {"policy_topic": "INVENTORY_AUDIT"},
        }

    if _contains_word_or_phrase(norm, [
        "trade in", "trade-in", "thu cu doi moi", "dinh gia may cu", "grade a", "grade b", "grade c", "grade d",
        "tro gia doi moi", "icloud an", "activation lock", "mdm", "mobile device management",
        "knox", "no cuoc", "blacklisted", "xoa trang du lieu", "zero data leak", "bien ban ban giao xoa du lieu"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.TRADE_IN_DATA_SECURITY,
            "tools": [],
            "parameters": {"policy_topic": "TRADE_IN"},
        }

    if _contains_word_or_phrase(norm, [
        "itil", "change advisory board", "cab", "standard change", "normal change", "emergency change",
        "thay doi tieu chuan", "thay doi thong thuong", "thay doi khan cap", "ke hoach rollback",
        "rollback 15 phut", "change freeze", "khung gio cam thay doi", "cam thay doi chieu thu sau",
        "pre-change snapshot", "request for change", "rfc"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.ITIL_CHANGE_MANAGEMENT,
            "tools": [],
            "parameters": {"policy_topic": "CHANGE_MANAGEMENT"},
        }

    if _contains_word_or_phrase(norm, [
        "nist 800-88", "nist sp 800-88", "tieu huy du lieu", "xoa du lieu", "degauss", "degausser",
        "10000 gauss", "10,000 gauss", "ata secure erase", "cryptographic erase",
        "nghien nat vat ly", "physical shredding", "duoi 2mm", "certificate of data destruction",
        "chung chi tieu huy du lieu"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.DATA_SANITIZATION_NIST,
            "tools": [],
            "parameters": {"policy_topic": "DATA_SANITIZATION"},
        }

    # 1d. Core Enterprise Handbook & Fundamental Corporate Policies (Applicable across all workspaces)
    if _contains_word_or_phrase(norm, [
        "gio lam viec", "thoi gio lam viec", "cham cong", "di muon", "ve som", "grace period",
        "nghi phep", "phep nam", "annual leave", "12 ngay phep", "don xin nghi phep", "chuyen phep",
        "nghi viec rieng", "nghi ket hon", "nghi tang", "nghi om", "nghi thai san", "c65", "bhxh"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.CORE_WORKING_HOURS_LEAVE,
            "tools": [],
            "parameters": {"policy_topic": "WORKING_HOURS_LEAVE"},
        }

    if _contains_word_or_phrase(norm, [
        "cong tac phi", "di cong tac", "per diem", "phu cap tien an", "tien khach san",
        "luu tru cong tac", "tam ung", "de nghi tam ung", "80% du toan", "hoan ung",
        "thanh toan cong tac phi", "quyet toan", "7 ngay lam viec", "hoa don gtgt", "e-invoice",
        "hoa don tren 5 trieu", "chuyen khoan cong tac"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.CORE_EXPENSE_TRAVEL_REIMBURSEMENT,
            "tools": [],
            "parameters": {"policy_topic": "EXPENSE_TRAVEL"},
        }

    if _contains_word_or_phrase(norm, [
        "mat khau may tinh", "do phuc tap mat khau", "doi mat khau", "90 ngay doi mat khau",
        "xac thuc hai lop", "mfa", "2fa", "clean desk", "clear screen", "khoa man hinh",
        "windows + l", "inactivity timeout", "10 phut tu dong khoa", "phan mem crack", "phan mem lau",
        "usb ngoai", "wifi cong cong", "bao mat noi bo"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.CORE_IT_SECURITY_DEVICE_USAGE,
            "tools": [],
            "parameters": {"policy_topic": "IT_SECURITY_DEVICE"},
        }

    if _contains_word_or_phrase(norm, [
        "onboarding", "nhan vien moi", "ngay dau tien", "ho so nhan su", "cap phat may tinh",
        "ban giao tai san", "buddy", "mentor", "thoi gian thu viec", "thu viec 2 thang", "thu viec 1 thang",
        "luong thu viec", "85% luong", "danh gia thu viec", "probation review", "75% kpi", "ky hop dong chinh thuc"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.CORE_ONBOARDING_PROBATION,
            "tools": [],
            "parameters": {"policy_topic": "ONBOARDING_PROBATION"},
        }

    if _contains_word_or_phrase(norm, [
        "van hoa doanh nghiep", "quy tac ung xu", "gia tri cot loi", "dress code", "trang phuc cong so",
        "smart casual", "business casual", "thu sau tu do", "casual friday", "dong phuc", "pantry",
        "khong gian chung", "xung dot noi bo", "hoa giai xung dot", "to giac an danh", "whistleblower"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.CORE_CODE_OF_CONDUCT_CULTURE,
            "tools": [],
            "parameters": {"policy_topic": "CODE_OF_CONDUCT"},
        }

    if _contains_word_or_phrase(norm, [
        "danh gia hieu suat", "xep loai kpi", "loai a", "loai b", "loai c", "loai d",
        "luong thang 13", "thuong tet", "thuong luong thang 13", "kham suc khoe", "kham dinh ky",
        "bao hiem suc khoe", "qua sinh nhat", "hieu hi", "du lich", "teambuilding", "company trip"
    ]) and not has_explicit_mutation:
        return {
            "intent": BusinessIntent.CORE_PERFORMANCE_BENEFITS_BONUS,
            "tools": [],
            "parameters": {"policy_topic": "BENEFITS_BONUS"},
        }


    # 2. Controlled Mutation Actions (Zero Direct Mutations)
    mutation_keywords = [
        "dieu chinh gia", "cap nhat gia", "doi gia", "tang gia", "giam gia",
        "phan cong", "giao viec", "dieu dong", "assign", "dispatch",
        "cap nhat trang thai", "chuyen trang thai", "update status",
        "lap lich", "tao nhiem vu", "schedule task", "dat lich",
        "xac nhan nhap hang", "nhan hang vao kho", "nhap kho",
        "tao phieu nhap", "tao phieu nhap kho", "de xuat tao phieu nhap", "de xuat nhap kho",
        "dieu chuyen", "dieu chuyen noi bo", "lap de xuat dieu chuyen", "de xuat dieu chuyen",
        "ha gia", "giam gia xa kho", "xa kho", "chuyen hang giua chi nhanh",
        "doi moi doa", "de xuat doi moi", "lap de xuat doi moi", "doi moi 100%",
        "de xuat phat", "lap de xuat phat", "phat nha cung cap", "phat giao tre",
        "de xuat chi vien", "dieu dong chi vien", "lap de xuat chi vien",
    ]
    is_read_only_transfer = _contains_word_or_phrase(norm, [
        "dieu chuyen ton kho", "chuyen hang giua", "chuyen giua cac chi nhanh",
        "dieu chuyen noi bo", "de xuat dieu chuyen",
    ]) and not has_explicit_mutation
    if _contains_word_or_phrase(norm, mutation_keywords) and not is_read_only_transfer and not _contains_word_or_phrase(norm, ["canh bao", "khi nao", "nguy co"]):
        return {
            "intent": BusinessIntent.MUTATION_ACTION,
            "tools": ["mutation_handler"],
            "parameters": {"query": query},
        }

    # 3. Root-Cause / "Vì sao?" Analysis
    if _contains_word_or_phrase(norm, ["vi sao", "tai sao", "do dau", "nguyen nhan gi", "dua vao dau", "ly do gi"]):
        target_t = "GENERAL"
        if _contains_word_or_phrase(norm, ["het hang", "ton kho", "nhap hang"]):
            target_t = "STOCKOUT_WARNING"
        elif _contains_word_or_phrase(norm, ["sla", "tre", "qua han", "cham"]):
            target_t = "SLA_AT_RISK"
        elif _contains_word_or_phrase(norm, ["de xuat", "chon", "ky thuat vien", "recommend"]):
            target_t = "RECOMMENDATION"
        elif _contains_word_or_phrase(norm, ["chi nhanh", "doanh thu", "canh bao", "giam"]):
            target_t = "BRANCH_WARNING"

        return {
            "intent": BusinessIntent.ROOT_CAUSE_EXPLANATION,
            "tools": ["explain_root_cause"],
            "parameters": {
                "target_type": target_t,
                "entity_name": category or extract_branch_name(query) or "",
            },
        }

    # 4. What-If / Scenario Simulation
    if _contains_word_or_phrase(norm, ["neu", "gia dinh", "mo phong", "gia su", "khi"]):
        if _contains_word_or_phrase(norm, ["doanh thu", "doanh so", "tien thu"]):
            m_pct = re.search(r"(\d+)\s*%", norm)
            pct_val = float(m_pct.group(1)) if m_pct else 10.0
            if any(w in norm for w in ["giam", "tut", "down"]):
                pct_val = -pct_val
            return {
                "intent": BusinessIntent.WHAT_IF_SIMULATION,
                "tools": ["simulate_what_if_scenario"],
                "parameters": {
                    "scenario_type": "REVENUE_CHANGE",
                    "change_pct": pct_val,
                },
            }
        elif _contains_word_or_phrase(norm, ["ticket", "su co", "yeu cau"]):
            m_pct = re.search(r"(\d+)\s*%", norm)
            pct_val = float(m_pct.group(1)) if m_pct else 20.0
            if any(w in norm for w in ["giam", "down"]):
                pct_val = -pct_val
            return {
                "intent": BusinessIntent.WHAT_IF_SIMULATION,
                "tools": ["simulate_what_if_scenario"],
                "parameters": {
                    "scenario_type": "TICKET_VOLUME_CHANGE",
                    "change_pct": pct_val,
                },
            }
        elif _contains_word_or_phrase(norm, ["ton", "con", "san pham", "chiec", "cai"]):
            m_units = re.search(r"(\d+)\s*(?:san pham|chiec|cai|don vi|unit)?", norm)
            unit_val = float(m_units.group(1)) if m_units else 5.0
            return {
                "intent": BusinessIntent.WHAT_IF_SIMULATION,
                "tools": ["simulate_what_if_scenario"],
                "parameters": {
                    "scenario_type": "STOCK_DEPLETION",
                    "param_value": unit_val,
                },
            }

    # 5. Multi-Step Composite Queries
    # 5a. Best selling + Low stock
    if _contains_word_or_phrase(norm, ["ban chay", "ban nhieu", "chay nhat"]) and _contains_word_or_phrase(norm, ["con it hang", "con bao nhieu", "ton kho thap", "con hang", "it hang nhat"]):
        return {
            "intent": BusinessIntent.TOP_SELLING_PRODUCTS,
            "tools": ["get_top_selling_products", "get_stock_balance_summary"],
            "parameters": {
                "category": category,
                "metric": "quantity_sold",
                "limit": 1,
                "time_label": time_label,
            },
        }

    # 5b. Riskiest Ticket + Suitable Technicians
    if _contains_word_or_phrase(norm, ["nguy hiem nhat", "sap tre", "nguy co tre"]) and _contains_word_or_phrase(norm, ["ai co the xu ly", "ai xu ly", "ai lam duoc", "ai phu hop"]):
        return {
            "intent": BusinessIntent.SERVICE_SLA_AT_RISK,
            "tools": ["get_service_ticket_summary", "get_recommendations"],
            "parameters": {
                "filter": "SLA_AT_RISK",
            },
        }

    # 5c. Nearest + Best Fit Technician
    if _contains_word_or_phrase(norm, ["gan nhat"]) and _contains_word_or_phrase(norm, ["phu hop nhat", "tot nhat", "nen giao"]):
        m_ticket = re.search(r"(?:ticket|phieu|yeu cau|request)\s*#?\s*(\d+)", norm)
        ticket_id = int(m_ticket.group(1)) if m_ticket else follow_up.get("ticket_id")
        return {
            "intent": BusinessIntent.TECHNICIAN_RECOMMENDATION,
            "tools": ["query_nearby_technicians", "get_recommendations"],
            "parameters": {"ticket_id": ticket_id, "radius_km": 25.0},
        }

    # 6. Customer Purchase History (Order history)
    if _contains_word_or_phrase(norm, ["da mua", "da mua gi", "da mua nhung gi", "tung mua", "lich su mua hang", "mua nhung gi"]):
        cust_name = extract_customer_name(query)
        return {
            "intent": BusinessIntent.CUSTOMER_ORDER_HISTORY,
            "tools": ["get_customer_order_history"],
            "parameters": {"customer_name": cust_name},
        }

    # 7. Technician Skills & Competencies (with optional availability)
    skill_match = extract_skill_keyword(query)
    is_doc_query = _contains_word_or_phrase(norm, ["quy trinh", "sop", "huong dan", "chinh sach", "quy dinh", "tieu chuan", "dieu khoan"])
    is_product_catalog_query = _contains_word_or_phrase(norm, ["model", "cac model", "danh sach san pham", "hien co", "bao nhieu"])
    is_person_skill_query = _contains_word_or_phrase(norm, ["ai", "ai co", "ky thuat vien", "nhan vien", "nguoi", "chuyen mon", "ky nang", "biet"])

    if (skill_match or _contains_word_or_phrase(norm, ["ky nang", "chuyen mon", "biet", "chuyen ve"])) and not is_doc_query and not is_product_catalog_query and is_person_skill_query:
        is_avail_only = _contains_word_or_phrase(norm, ["ranh", "san sang", "available", "dang ranh"])
        return {
            "intent": BusinessIntent.TECHNICIAN_SKILLS,
            "tools": ["get_technician_skills_summary"],
            "parameters": {
                "skill": skill_match or "",
                "is_available_only": is_avail_only,
            },
        }

    # 8. Technician Schedule & Calendar / Conflict Check
    if _contains_word_or_phrase(norm, ["lich", "lich lam viec", "trung lich", "chong cheo", "chieu mai", "lich bận", "lich trong"]):
        is_conflict = _contains_word_or_phrase(norm, ["trung lich", "chong cheo", "xung dot"])
        date_t = "tomorrow" if _contains_word_or_phrase(norm, ["mai", "ngay mai", "chieu mai"]) else "today"
        emp_match = None
        m_emp = re.search(r"(?:ky\s*thuat\s*vien|nhan\s*vien|tho)\s+([A-Za-z0-9\s_]+?)(?=\s*(?:hom\s*nay|ngay\s*mai|co\s*lich|la|,|\?|$))", norm, re.IGNORECASE)
        if m_emp and m_emp.group(1).strip() and m_emp.group(1).lower() not in ["nao", "gi"]:
            emp_match = m_emp.group(1).strip().title()

        return {
            "intent": BusinessIntent.TECHNICIAN_SCHEDULE,
            "tools": ["get_technician_schedule_summary"],
            "parameters": {
                "date_target": date_t,
                "employee_query": emp_match,
                "conflict_check": is_conflict,
            },
        }

    # 9. Spatial Ticket Clustering & Hotspots
    if _contains_word_or_phrase(norm, ["khu vuc nao", "tap trung nhieu", "nhieu ticket nhat", "hotspot", "cum su co", "tap trung su co"]):
        return {
            "intent": BusinessIntent.GIS_TICKET_CLUSTERING,
            "tools": ["get_spatial_ticket_clusters"],
            "parameters": {},
        }

    # 10. Period & Sales Trend Analysis
    is_trend_query = _contains_word_or_phrase(norm, [
        "tang hay giam", "tang truong", "sut giam", "xu huong", "bien dong",
        "tang manh", "giam manh", "on dinh", "tang doanh so", "giam doanh so",
        "so voi thang truoc", "so voi tuan truoc", "so voi cung ky", "dien bien",
        "tang truong hay sut giam"
    ])
    if is_trend_query:
        branch_name = extract_branch_name(query)
        return {
            "intent": BusinessIntent.SALES_TREND,
            "tools": ["get_sales_trend_analytics"],
            "parameters": {
                "category": category,
                "branch_name": branch_name,
                "period_days": 30 if "thang" in norm else (7 if "tuan" in norm else 30),
                "time_label": time_label,
            },
        }

    # 11. Entity & Branch Comparison
    has_comparison_keywords = _contains_word_or_phrase(norm, [
        "so voi", "cai nao ban chay hon", "ben nao tot hon", "cai nao hon",
        "hang nao tot hon", "thuong hieu nao", "so sanh", "cai nao nhieu hon",
        "doanh thu ben nao", "cai nao cao hon"
    ]) or (
        _contains_word_or_phrase(norm, ["hay", "va"]) and
        _contains_word_or_phrase(norm, ["ban tot hon", "tot hon", "cao hon", "chay hon", "nhieu hon", "chiec hon", "duoc nhieu hon"])
    )
    if has_comparison_keywords and not is_trend_query:
        ent_type, compared_list = extract_comparison_entities(query)
        if compared_list or _contains_word_or_phrase(norm, ["so sanh", "cai nao", "ben nao", "so voi"]):
            comp_metric = "revenue" if _contains_word_or_phrase(norm, ["doanh thu", "doanh so", "tien"]) else "quantity_sold"
            return {
                "intent": BusinessIntent.COMPARISON,
                "tools": ["compare_entities_analytics"],
                "parameters": {
                    "entity_type": ent_type,
                    "entities": compared_list,
                    "metric": comp_metric,
                    "start_date": start_date,
                    "end_date": end_date,
                    "time_label": time_label,
                },
            }

    # 12. Time-series Forecast Queries (XGBoost)
    if _contains_word_or_phrase(norm, ["du bao", "forecast", "du doan", "14 ngay toi", "tuan toi", "thoi gian toi", "uoc tinh", "sap toi"]):
        target = "RETAIL_REVENUE" if ws_type == "RETAIL" else "SERVICE_TICKET_VOLUME"
        if _contains_word_or_phrase(norm, ["ticket", "phieu yeu cau", "phieu su co", "su co"]):
            target = "SERVICE_TICKET_VOLUME"
        elif _contains_word_or_phrase(norm, ["don hang", "order", "so luong don", "luong don"]):
            target = "RETAIL_ORDER_VOLUME"
        elif _contains_word_or_phrase(norm, ["doanh thu", "revenue", "sales", "tien thu"]):
            target = "RETAIL_REVENUE"
        return {
            "intent": BusinessIntent.FORECAST_METRICS,
            "tools": ["get_forecast"],
            "parameters": {"target_type": target},
        }

    # 13. GIS Proximity & Nearest Technician (Distance-based)
    has_proximity_search = (
        _contains_word_or_phrase(norm, ["gan nhat", "trong ban kinh", "cach bao xa", "khu vuc nao", "xung quanh", "trong pham vi", "khoang cach"])
        or bool(re.search(r"gan\s+(?:ticket|phieu|yeu cau|request)\s*#?\s*\d+", norm))
        or (bool(re.search(r"(?:ticket|phieu)\s*#?\s*\d+", norm)) and _contains_word_or_phrase(norm, ["gan", "gan nhat"]))
    )
    if has_proximity_search:
        m_ticket = re.search(r"(?:ticket|phieu|yeu cau|request)\s*#?\s*(\d+)", norm)
        ticket_id = int(m_ticket.group(1)) if m_ticket else follow_up.get("ticket_id")
        return {
            "intent": BusinessIntent.TECHNICIAN_NEARBY_GIS,
            "tools": ["query_nearby_technicians"],
            "parameters": {"ticket_id": ticket_id, "radius_km": 25.0},
        }

    # 14. Technician Recommendation (Best fit / Skill + Workload + Distance) vs Workload
    if _contains_word_or_phrase(norm, ["ky thuat vien", "technician", "tho", "ky su", "nhan vien ky thuat", "nguoi xu ly", "ai dang ranh", "ranh nhat", "ai ranh", "nhan viec", "ai nen xu ly"]):
        if _contains_word_or_phrase(norm, ["phu hop nhat", "nen giao cho ai", "ai nen xu ly", "ai co the nhan", "ai co ky nang", "phu hop"]):
            m_ticket = re.search(r"(?:ticket|phieu|yeu cau|request)\s*#?\s*(\d+)", norm)
            ticket_id = int(m_ticket.group(1)) if m_ticket else follow_up.get("ticket_id")
            return {
                "intent": BusinessIntent.TECHNICIAN_RECOMMENDATION,
                "tools": ["get_recommendations", "query_nearby_technicians"] if ticket_id else ["get_recommendations", "get_technician_workload_summary"],
                "parameters": {"ticket_id": ticket_id},
            }
        elif _contains_word_or_phrase(norm, ["qua tai", "ban nhat", "nhieu viec", "score cao", "ranh nhat", "san sang", "danh sach", "tai cong viec", "nao dang", "nhan viec"]):
            return {
                "intent": BusinessIntent.TECHNICIAN_WORKLOAD,
                "tools": ["get_technician_workload_summary"],
                "parameters": {"sort_order": sort_order, "limit": limit},
            }

    # 15. Service Labor Cost & Hours (LaborEntry aggregation)
    if _contains_word_or_phrase(norm, [
        "chi phi nhan cong", "tien cong", "gio cong", "thoi gian lam", "cong ky thuat",
        "ton bao nhieu gio", "lam bao lau", "chi phi xu ly", "chi phi ticket", "tien luong cong"
    ]):
        m_ticket = re.search(r"(?:ticket|phieu|yeu cau|request)\s*#?\s*(\d+)", norm)
        ticket_id = int(m_ticket.group(1)) if m_ticket else follow_up.get("ticket_id")
        return {
            "intent": BusinessIntent.SERVICE_LABOR_COST,
            "tools": ["get_service_labor_cost_summary"],
            "parameters": {
                "ticket_id": ticket_id,
                "start_date": start_date,
                "end_date": end_date,
                "time_label": time_label,
            },
        }

    # 16. IT Service Catalog Queries
    if _contains_word_or_phrase(norm, [
        "goi dich vu", "loai dich vu", "danh muc dich vu", "cac dich vu", "bang gia dich vu",
        "dich vu bao tri", "dich vu cai dat", "dich vu sua chua", "dich vu database"
    ]):
        return {
            "intent": BusinessIntent.SERVICE_CATALOG,
            "tools": ["get_service_catalog_summary"],
            "parameters": {"category": category},
        }

    # 16b. Profit Margins & Cost of Goods Sold Analytics
    if _contains_word_or_phrase(norm, [
        "bien loi nhuan", "ty suat loi nhuan", "loi nhuan gop", "margin", "gia von", "loi nhuan danh muc"
    ]):
        return {
            "intent": BusinessIntent.PROFIT_MARGIN_ANALYSIS,
            "tools": ["get_category_profit_margins"],
            "parameters": {"category": category},
        }

    # 16c. Customer Churn Risk & Retention Guidelines
    if _contains_word_or_phrase(norm, [
        "churn", "roi bo", "nguy co roi bo", "khach hang vang lai", "chua mua lai",
        "khong mua hang", "khong phat sinh", "khach hang at-risk"
    ]):
        return {
            "intent": BusinessIntent.CUSTOMER_CHURN_RISK,
            "tools": ["get_customer_churn_risk_summary"],
            "parameters": {"inactivity_days": 45},
        }

    # 16d. Inter-branch Inventory Transfer & Balancing
    if _contains_word_or_phrase(norm, [
        "dieu chuyen ton kho", "can doi ton kho", "chuyen hang giua",
        "thieu hut tai", "chuyen giua cac chi nhanh", "dieu chuyen noi bo", "de xuat dieu chuyen"
    ]):
        return {
            "intent": BusinessIntent.INTER_BRANCH_TRANSFER,
            "tools": ["get_inter_branch_transfer_recommendations"],
            "parameters": {},
        }

    # 16e. Field Technician Safety & Overtime Compliance
    if _contains_word_or_phrase(norm, [
        "gio lam them", "overtime", "lam them gio", "an toan lao dong",
        "phu cap ca dem", "iso 27001", "qua tai", "chung chi ky thuat", "an toan dien"
    ]):
        return {
            "intent": BusinessIntent.TECHNICIAN_COMPLIANCE,
            "tools": ["get_technician_safety_compliance"],
            "parameters": {},
        }

    # 17. Document RAG (Pure Policy / SOP without specific live metrics query)
    is_pure_rag = _contains_word_or_phrase(norm, [
        "chinh sach", "quy dinh", "quy trinh", "sop", "huong dan", "tai lieu", "tieu chuan", "dieu khoan"
    ]) and not _contains_word_or_phrase(norm, [
        "ban chay", "doanh thu", "doanh so", "cao nhat", "thap nhat", "nhieu nhat", "it nhat", "top"
    ]) and not re.search(r"(?:ticket|phieu)\s*#?\s*\d+", norm)

    if is_pure_rag:
        return {
            "intent": BusinessIntent.DOCUMENT_RAG,
            "tools": [],
            "parameters": {},
        }

    # 18. Service Tickets / Single Ticket Lookup / SLA Details
    is_co_phieu = _contains_word_or_phrase(norm, ["co phieu", "chung khoan", "hang khong", "boeing"])
    if _contains_word_or_phrase(norm, ["ticket", "phieu", "phieu yeu cau", "phieu su co", "su co", "sla", "yeu cau dich vu", "case"]) and not is_co_phieu:
        m_ticket = re.search(r"(?:ticket|phieu|yeu cau|request|case)\s*#?\s*(\d+)", norm)

        # Check single ticket lookup e.g. "Ticket 5 đang ở trạng thái gì?", "Phiếu #12 ai phụ trách?", "Ticket 5 sắp trễ SLA..."
        if m_ticket and not _contains_word_or_phrase(norm, ["co bao nhieu", "top", "danh sach", "tat ca", "nhung"]):
            return {
                "intent": BusinessIntent.TICKET_LOOKUP,
                "tools": ["get_service_ticket_summary"],
                "parameters": {"ticket_id": int(m_ticket.group(1))},
            }

        # SLA At Risk vs Breached
        if _contains_word_or_phrase(norm, ["sap tre", "nguy co tre", "at risk", "con 1 gio", "con bao lau", "nguy hiem nhat", "con duoi", "duoi 2", "duoi 4"]):
            return {
                "intent": BusinessIntent.SERVICE_SLA_AT_RISK,
                "tools": ["get_service_ticket_summary"],
                "parameters": {"filter": "SLA_AT_RISK", "ticket_id": int(m_ticket.group(1)) if m_ticket else None},
            }
        elif _contains_word_or_phrase(norm, ["vi pham", "qua han", "tre sla", "breached", "cham tre"]):
            return {
                "intent": BusinessIntent.SERVICE_SLA_AT_RISK,
                "tools": ["get_service_ticket_summary"],
                "parameters": {"filter": "SLA_BREACHED", "ticket_id": int(m_ticket.group(1)) if m_ticket else None},
            }

        return {
            "intent": BusinessIntent.SERVICE_TICKETS_SUMMARY,
            "tools": ["get_service_ticket_summary"],
            "parameters": {
                "exclude_closed": exclusions.get("exclude_closed", False),
            },
        }


    # 19. Recommendations Engine Alerts
    if _contains_word_or_phrase(norm, ["de xuat", "khuyen nghi", "recommendation", "canh bao", "giai phap"]):
        if _contains_word_or_phrase(norm, ["het hang", "ton kho", "nhap hang", "nhap them", "thieu hang", "can nhap", "nhap som"]):
            return {
                "intent": BusinessIntent.STOCKOUT_RISK,
                "tools": ["get_stockout_risk_summary"],
                "parameters": {"category": category, "limit": limit},
            }
        return {
            "intent": BusinessIntent.RECOMMENDATIONS,
            "tools": ["get_recommendations"],
            "parameters": {},
        }

    # 20. Stockout Risk Prediction & Reorder Alert
    if _contains_word_or_phrase(norm, [
        "het hang", "nguy co het hang", "sap het hang", "thieu hang", "thieu laptop",
        "thieu san pham", "ton kho thap", "canh bao ton kho", "de xuat nhap", "de xuat nhap them",
        "can nhap them", "can nhap som", "du kien het hang", "khi nao het hang", "sap het", "dang thieu",
        "nen nhap", "nhap som", "nen nhap som"
    ]):
        return {
            "intent": BusinessIntent.STOCKOUT_RISK,
            "tools": ["get_stockout_risk_summary"],
            "parameters": {"category": category, "limit": limit},
        }

    # 21. Stock Balance / Inventory On-Hand Queries
    if _contains_word_or_phrase(norm, [
        "ton kho", "ton kho hien tai", "so luong ton", "so luong trong kho",
        "con bao nhieu", "con bao nhieu cai", "con hang khong", "con trong kho",
        "ton hien tai", "kiem tra ton", "so luong con lai", "ton thap", "ton an toan",
        "it hang nhat", "con it hang"
    ]):
        return {
            "intent": BusinessIntent.STOCK_BALANCE,
            "tools": ["get_stock_balance_summary"],
            "parameters": {"category": category, "limit": limit},
        }

    # 22. Customer Analytics (Top Customers, Customer Summary)
    if _contains_word_or_phrase(norm, ["khach hang", "customer", "khach mua", "khach", "nguoi mua"]):
        branch_name = extract_branch_name(query)
        if _contains_word_or_phrase(norm, ["nhieu nhat", "mua nhieu", "top", "doanh thu cao", "vip", "chi tieu", "mua nhieu laptop", "mang lai doanh thu"]):
            return {
                "intent": BusinessIntent.TOP_CUSTOMERS,
                "tools": ["get_top_customers"],
                "parameters": {
                    "limit": limit,
                    "category": category,
                    "branch": branch_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "time_label": time_label,
                    "exclude_cancelled": exclusions.get("exclude_cancelled", True),
                },
            }
        elif _contains_word_or_phrase(norm, ["bao nhieu khach", "danh sach khach", "phan khuc", "co bao nhieu khach"]):
            return {
                "intent": BusinessIntent.CUSTOMER_SUMMARY,
                "tools": ["get_customer_summary"],
                "parameters": {},
            }

    # 23. Branch Analytics & Rankings (Targeting Branch entity rankings)
    is_branch_ranking_target = (
        _contains_word_or_phrase(norm, ["top chi nhanh", "top 3 chi nhanh", "top 5 chi nhanh", "cac chi nhanh", "xep hang chi nhanh"])
        or (bool(re.search(r"\b(?:chi\s*nhanh|cua\s*hang|co\s*so|diem\s*ban)\s*nao\b", norm)) and _contains_word_or_phrase(norm, ["doanh thu", "ban chay", "tot nhat", "thap nhat", "cao nhat", "ban nhieu", "ban duoc", "nhieu", "doanh so"]))
    )
    if is_branch_ranking_target:

        return {
            "intent": BusinessIntent.BRANCH_REVENUE,
            "tools": ["get_branch_sales_analytics"],
            "parameters": {
                "sort_order": sort_order,
                "start_date": start_date,
                "end_date": end_date,
                "time_label": time_label,
                "category": category,
            },
        }


    # 24. Top Selling / Revenue Products (Product Performance Rankings)
    is_sales_ranking = _contains_word_or_phrase(norm, [
        "ban chay", "ban nhieu", "mua nhieu", "chay nhat", "ban duoc nhieu",
        "so luong ban", "ban it", "ban duoc it", "ban chay nhat", "tieu thu nhieu",
        "luong ban cao", "ban cham", "e am", "dung dau", "dung cuoi"
    ])
    is_revenue_ranking = _contains_word_or_phrase(norm, [
        "doanh thu cao", "doanh thu nhieu", "doanh thu thap", "doanh thu lon",
        "mang lai doanh thu", "doanh so cao", "tien ban ra", "kiem duoc nhieu tien"
    ])

    if is_sales_ranking or is_revenue_ranking or (category and _contains_word_or_phrase(norm, ["ban chay", "ban nhieu", "mua nhieu", "doanh thu cao", "chay nhat"])):
        metric = "revenue" if is_revenue_ranking and not is_sales_ranking else "quantity_sold"
        branch_name = extract_branch_name(query)
        return {
            "intent": BusinessIntent.TOP_SELLING_PRODUCTS if metric == "quantity_sold" else BusinessIntent.TOP_REVENUE_PRODUCTS,
            "tools": ["get_top_selling_products"],
            "parameters": {
                "category": category,
                "branch": branch_name,
                "metric": metric,
                "sort_order": sort_order,
                "limit": limit,
                "start_date": start_date,
                "end_date": end_date,
                "time_label": time_label,
                "exclude_cancelled": exclusions.get("exclude_cancelled", True),
                "active_only": exclusions.get("active_only", False),
            },
        }

    # 25. Catalog count & list
    catalog_count_patterns = [
        "co bao nhieu", "bao nhieu san pham", "so luong san pham",
        "bao nhieu laptop", "bao nhieu dien thoai", "bao nhieu mat hang",
        "danh sach san pham", "danh sach laptop", "danh sach hang hoa",
        "dang kinh doanh", "hien co", "hien tai co", "san pham nao dang",
        "cac mau may", "model", "thiet bi", "danh muc", "tong so mat hang", "tong so", "mat hang", "tat ca san pham"
    ]
    if _contains_word_or_phrase(norm, catalog_count_patterns):
        return {
            "intent": BusinessIntent.CATALOG_COUNT,
            "tools": ["get_product_catalog_summary"],
            "parameters": {"category": category},
        }

    # 26. Overall Sales / Revenue Summary
    if _contains_word_or_phrase(norm, ["doanh thu", "doanh so", "tong thu", "tong tien", "ban duoc bao nhieu", "ban hang", "tong gia tri"]):
        return {
            "intent": BusinessIntent.SALES_SUMMARY,
            "tools": ["get_sales_summary"],
            "parameters": {
                "start_date": start_date,
                "end_date": end_date,
                "time_label": time_label,
                "exclude_cancelled": exclusions.get("exclude_cancelled", True),
            },
        }

    # 27. Default to Document RAG (Searches workspace knowledge base)
    return {
        "intent": BusinessIntent.DOCUMENT_RAG,
        "tools": [],
        "parameters": {},
    }
