"""
Controlled Tool Registry System (Phase 10).
Defines schema-validated, permission-enforced READ and MUTATION tools for AI Assistant and Decision Support.
"""

from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass, field
from decimal import Decimal
from django.db import transaction

from apps.workspaces.models import Workspace
from apps.accounts.models import User
from apps.accounts.services import has_workspace_permission


class ToolException(Exception):
    """Base exception for tool execution errors."""
    pass


class ToolPermissionDenied(ToolException):
    """Raised when user lacks required permission for a tool."""
    pass


class ToolValidationError(ToolException):
    """Raised when input parameters fail schema or business validation."""
    pass


@dataclass
class ToolDefinition:
    name: str
    description: str
    classification: str  # "READ" or "MUTATION"
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    required_permission: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    handler: Callable[[Workspace, User, Dict[str, Any]], Dict[str, Any]]


def validate_action_contract(tool_def: ToolDefinition, workspace: Workspace, parameters: Dict[str, Any]) -> None:
    """Validate the typed action contract before an approval is persisted.

    Schema validation alone is not enough for mutation proposals: IDs must
    resolve inside the active workspace and quantities/prices must satisfy
    domain invariants.  This validator deliberately performs no writes.
    """
    if not isinstance(parameters, dict):
        raise ToolValidationError("Action parameters must be an object.")

    properties = tool_def.input_schema.get("properties", {})
    for field_name, spec in properties.items():
        if field_name not in parameters or parameters[field_name] is None:
            continue
        value = parameters[field_name]
        expected = spec.get("type")
        valid = {
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "number": isinstance(value, (int, float, Decimal)) and not isinstance(value, bool),
            "string": isinstance(value, str),
            "array": isinstance(value, list),
            "object": isinstance(value, dict),
            "boolean": isinstance(value, bool),
        }.get(expected, True)
        if not valid:
            raise ToolValidationError(f"Parameter '{field_name}' must be of type {expected}.")

    if tool_def.classification != "MUTATION":
        return

    name = tool_def.name
    if name == "create_stock_transfer":
        from apps.retail.models import Branch, Product, StockBalance
        source_id = parameters.get("source_branch_id")
        destination_id = parameters.get("destination_branch_id")
        product_id = parameters.get("product_id")
        quantity = parameters.get("quantity")
        if quantity is None or quantity <= 0:
            raise ToolValidationError("quantity must be greater than zero.")
        if source_id == destination_id:
            raise ToolValidationError("Source and destination branches must be different.")
        if not Branch.objects.for_workspace(workspace).filter(id__in=[source_id, destination_id]).count() == 2:
            raise ToolValidationError("Both transfer branches must belong to the active workspace.")
        if not Product.objects.for_workspace(workspace).filter(id=product_id).exists():
            raise ToolValidationError("Transfer product must belong to the active workspace.")
        available = StockBalance.objects.filter(
            workspace=workspace, branch_id=source_id, product_id=product_id
        ).values_list("quantity_on_hand", flat=True).first()
        if available is not None and quantity > available:
            raise ToolValidationError("Transfer quantity exceeds source stock.")
    elif name == "adjust_product_price":
        from apps.retail.models import Product
        try:
            price = Decimal(str(parameters.get("new_price")))
        except Exception as exc:
            raise ToolValidationError("new_price must be a valid numeric value.") from exc
        if price <= 0:
            raise ToolValidationError("new_price must be greater than zero.")
        if not Product.objects.for_workspace(workspace).filter(id=parameters.get("product_id")).exists():
            raise ToolValidationError("Product must belong to the active workspace.")
    elif name in {"dispatch_technician", "schedule_task"}:
        from apps.service_ops.models import Employee, ServiceRequest
        employee_id = parameters.get("employee_id")
        if employee_id is not None and not Employee.objects.for_workspace(workspace).filter(id=employee_id).exists():
            raise ToolValidationError("Employee must belong to the active workspace.")
        ticket_id = parameters.get("ticket_id")
        if ticket_id is not None and not ServiceRequest.objects.for_workspace(workspace).filter(id=ticket_id).exists():
            raise ToolValidationError("Service request must belong to the active workspace.")
    elif name == "update_order_status":
        from apps.retail.models import Order, OrderStatus
        if not Order.objects.for_workspace(workspace).filter(id=parameters.get("order_id")).exists():
            raise ToolValidationError("Order must belong to the active workspace.")
        if parameters.get("new_status") not in {value for value, _ in OrderStatus.choices}:
            raise ToolValidationError("new_status is not a valid order status.")
    elif name == "create_goods_receipt":
        from apps.retail.models import Branch, Product, Supplier
        if not Supplier.objects.for_workspace(workspace).filter(id=parameters.get("supplier_id")).exists():
            raise ToolValidationError("Supplier must belong to the active workspace.")
        if not Branch.objects.for_workspace(workspace).filter(id=parameters.get("branch_id")).exists():
            raise ToolValidationError("Branch must belong to the active workspace.")
        items = parameters.get("items")
        if not items:
            raise ToolValidationError("items must contain at least one line.")
        for item in items:
            if not isinstance(item, dict) or item.get("quantity", 0) <= 0 or item.get("unit_cost", 0) < 0:
                raise ToolValidationError("Each receipt line requires positive quantity and non-negative unit_cost.")
            if not Product.objects.for_workspace(workspace).filter(id=item.get("product_id")).exists():
                raise ToolValidationError("Receipt product must belong to the active workspace.")
    elif name == "receive_goods_receipt":
        from apps.retail.models import GoodsReceipt
        if not GoodsReceipt.objects.for_workspace(workspace).filter(id=parameters.get("receipt_id")).exists():
            raise ToolValidationError("Goods receipt must belong to the active workspace.")


class ToolRegistry:
    _tools: Dict[str, ToolDefinition] = {}

    @classmethod
    def register(cls, tool_def: ToolDefinition):
        cls._tools[tool_def.name] = tool_def

    @classmethod
    def get(cls, name: str) -> Optional[ToolDefinition]:
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "classification": t.classification,
                "risk_level": t.risk_level,
                "required_permission": t.required_permission,
                "input_schema": t.input_schema,
            }
            for t in cls._tools.values()
        ]


# -------------------------------------------------------------------------
# READ TOOL HANDLERS
# -------------------------------------------------------------------------

def handle_get_sales_summary(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_sales_summary
    return get_sales_summary(workspace, user, **params)


def handle_get_order_summary(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.retail.models import Order, OrderStatus
    from django.db.models import Sum, Count

    qs = Order.objects.for_workspace(workspace)
    total_count = qs.count()
    completed = qs.filter(status=OrderStatus.COMPLETED).count()
    pending = qs.filter(status__in=[OrderStatus.PENDING, OrderStatus.CONFIRMED]).count()
    cancelled = qs.filter(status=OrderStatus.CANCELLED).count()

    total_val = float(qs.exclude(status=OrderStatus.CANCELLED).aggregate(s=Sum("total_amount"))["s"] or 0.0)

    return {
        "workspace": workspace.code,
        "total_orders": total_count,
        "completed_orders": completed,
        "pending_orders": pending,
        "cancelled_orders": cancelled,
        "total_valid_revenue_vnd": total_val,
    }


def handle_get_service_ticket_summary(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_service_ticket_summary
    return get_service_ticket_summary(workspace, user, **params)


def handle_get_technician_workload(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_technician_workload_summary
    return get_technician_workload_summary(workspace, user, **params)


def handle_query_nearby_technicians(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.gis.services import find_nearby_technicians
    from apps.recommendations.scoring import calculate_technician_score
    ticket_id = params.get("ticket_id")
    radius_km = float(params.get("radius_km", 25.0))
    res = find_nearby_technicians(workspace, service_request_id=ticket_id, radius_km=radius_km)
    candidates = res.get("candidates", [])
    for c in candidates:
        sc = calculate_technician_score(
            distance_km=c.get("distance_km", 0.0),
            active_tasks=c.get("active_tasks", 0),
            has_matching_skill=True,
            is_available=True,
            hourly_labor_rate=c.get("hourly_labor_rate"),
        )
        c["total_score"] = sc["score"]
        c["subscores"] = sc["subscores"]
    candidates.sort(key=lambda x: x.get("total_score", 0.0), reverse=True)
    res["candidates"] = candidates
    return res


def handle_get_forecast(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.forecasting.services import get_forecast_chart_data
    target_type = params.get("target_type")
    return get_forecast_chart_data(workspace, target_type=target_type)


def handle_get_recommendations(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.recommendations.models import Recommendation, RecommendationStatus
    from apps.recommendations.serializers import RecommendationSerializer
    status_filter = params.get("status", RecommendationStatus.PENDING)
    qs = Recommendation.objects.for_workspace(workspace).filter(status=status_filter)
    return {"count": qs.count(), "recommendations": RecommendationSerializer(qs, many=True).data}


# -------------------------------------------------------------------------
# MUTATION TOOL HANDLERS
# -------------------------------------------------------------------------

def handle_dispatch_technician(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.service_ops.models import ServiceRequest, Employee, Task, ServiceRequestStatus, TaskStatus

    ticket_id = params.get("ticket_id")
    employee_id = params.get("employee_id")

    req = ServiceRequest.objects.for_workspace(workspace).filter(id=ticket_id).first()
    if not req:
        raise ToolValidationError(f"Service Request ID #{ticket_id} not found in active workspace.")

    emp = Employee.objects.for_workspace(workspace).filter(id=employee_id).first()
    if not emp:
        raise ToolValidationError(f"Employee ID #{employee_id} not found in active workspace.")

    if not emp.is_active:
        raise ToolValidationError(f"Employee {emp.full_name} is currently inactive.")

    with transaction.atomic():
        # Update ServiceRequest
        req.assigned_employee = emp
        req.status = ServiceRequestStatus.IN_PROGRESS
        req.save()

        # Create or update associated task safely
        task = Task.objects.filter(service_request=req, assigned_to=emp).first()
        if not task:
            task = Task.objects.filter(service_request=req).first()
        if task:
            task.assigned_to = emp
            task.status = TaskStatus.IN_PROGRESS
            task.save(update_fields=["assigned_to", "status", "updated_at"])
        else:
            task = Task.objects.create(
                service_request=req,
                title=f"Phân công xử lý ticket #{req.request_number or req.id}",
                assigned_to=emp,
                status=TaskStatus.IN_PROGRESS,
                description=f"Công việc phân công trực tiếp cho kỹ thuật viên {emp.full_name}.",
            )

    return {
        "status": "SUCCESS",
        "ticket_id": req.id,
        "ticket_code": req.request_number,
        "assigned_employee_id": emp.id,
        "assigned_employee_name": emp.full_name,
        "new_ticket_status": req.status,
        "task_id": task.id,
    }


def handle_update_order_status(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.retail.models import Order, OrderStatus

    order_id = params.get("order_id")
    new_status = params.get("new_status")

    if new_status not in [c[0] for c in OrderStatus.choices]:
        raise ToolValidationError(f"Invalid order status '{new_status}'. Allowed: {[c[0] for c in OrderStatus.choices]}")

    order = Order.objects.for_workspace(workspace).filter(id=order_id).first()
    if not order:
        raise ToolValidationError(f"Order ID #{order_id} not found in active workspace.")

    # Business state machine validation
    if order.status == OrderStatus.CANCELLED and new_status != OrderStatus.CANCELLED:
        raise ToolValidationError(f"Đơn hàng #{order_id} đã bị HỦY (CANCELLED) và không thể chuyển sang trạng thái '{new_status}'.")
    if order.status == OrderStatus.COMPLETED and new_status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
        raise ToolValidationError(f"Đơn hàng #{order_id} đã HOÀN THÀNH (COMPLETED) và không thể hoàn tác về trạng thái '{new_status}'.")

    with transaction.atomic():
        old_status = order.status
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])

    return {
        "status": "SUCCESS",
        "order_id": order.id,
        "order_code": getattr(order, "order_number", getattr(order, "code", str(order.id))),
        "old_status": old_status,
        "new_status": order.status,
    }


def handle_schedule_task(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.service_ops.models import ServiceRequest, Task, Employee, TaskStatus

    title = params.get("title", "Công việc lập lịch mới")
    employee_id = params.get("employee_id")
    ticket_id = params.get("ticket_id")

    emp = None
    if employee_id:
        emp = Employee.objects.for_workspace(workspace).filter(id=employee_id).first()
        if not emp:
            raise ToolValidationError(f"Employee ID #{employee_id} not found in workspace.")

    req = ServiceRequest.objects.for_workspace(workspace).filter(id=ticket_id).first() if ticket_id else ServiceRequest.objects.for_workspace(workspace).first()
    if not req:
        raise ToolValidationError("No ServiceRequest available in workspace to bind task.")

    task = Task.objects.create(
        service_request=req,
        title=title,
        assigned_to=emp,
        status=TaskStatus.PENDING,
        description=params.get("description", "Lập lịch từ hệ thống Hỗ trợ Ra quyết định."),
    )

    return {
        "status": "SUCCESS",
        "task_id": task.id,
        "title": task.title,
        "assigned_to": emp.full_name if emp else None,
        "task_status": task.status,
    }


def handle_adjust_product_price(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adjusts the commercial unit price of a product in the workspace.
    Domain-grounded mutation for Retail recommendations.
    Requires 'retail.change_product'.
    """
    from apps.retail.models import Product

    product_id = params.get("product_id")
    new_price = params.get("new_price")

    if product_id is None:
        raise ToolValidationError("Parameter 'product_id' is required.")
    if new_price is None:
        raise ToolValidationError("Parameter 'new_price' is required.")

    try:
        new_price_val = Decimal(str(new_price))
    except Exception:
        raise ToolValidationError(f"Invalid new_price value '{new_price}'. Must be a valid numeric price.")

    if new_price_val <= Decimal("0.00"):
        raise ToolValidationError("Parameter 'new_price' must be strictly greater than 0.")

    product = Product.objects.for_workspace(workspace).filter(id=product_id).first()
    if not product:
        raise ToolValidationError(f"Product ID #{product_id} not found in active workspace.")

    with transaction.atomic():
        old_price = product.unit_price
        product.unit_price = new_price_val
        product.save(update_fields=["unit_price", "updated_at"])

    return {
        "status": "SUCCESS",
        "product_id": product.id,
        "sku": product.sku,
        "name": product.name,
        "old_price": float(old_price),
        "new_price": float(product.unit_price),
        "message": f"Giá bán của sản phẩm '{product.name}' ({product.sku}) đã được điều chỉnh từ {old_price:,.0f} VND sang {new_price_val:,.0f} VND.",
    }


def handle_create_promotion_request(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    [DEPRECATED] Generic promotional placeholder.
    Replaced by 'adjust_product_price' which directly mutates Product.unit_price.
    """
    promotion_name = params.get("promotion_name")
    discount_pct = params.get("discount_pct", 10)

    if not promotion_name:
        raise ToolValidationError("Parameter 'promotion_name' is required.")

    return {
        "status": "SUCCESS",
        "promotion_name": promotion_name,
        "discount_pct": discount_pct,
        "message": f"Chương trình khuyến mãi '{promotion_name}' ({discount_pct}%) đã được ghi nhận. (DEPRECATED: Khuyến nghị dùng 'adjust_product_price')",
        "deprecated": True,
    }

    return {
        "status": "SUCCESS",
        "promotion_name": promotion_name,
        "discount_pct": discount_pct,
        "message": f"Chương trình khuyến mãi '{promotion_name}' ({discount_pct}%) đã được ghi nhận thành công.",
    }


# -------------------------------------------------------------------------
# REGISTER ALL TOOLS IN REGISTRY
# -------------------------------------------------------------------------

# Read tools
ToolRegistry.register(ToolDefinition(
    name="get_sales_summary",
    description="Truy vấn tổng quan doanh thu và số lượng đơn hàng lẻ theo workspace",
    classification="READ",
    risk_level="LOW",
    required_permission="retail.view_order",
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "object"},
    handler=handle_get_sales_summary,
))

ToolRegistry.register(ToolDefinition(
    name="get_order_summary",
    description="Thống kê phân loại trạng thái các đơn hàng retail trong workspace",
    classification="READ",
    risk_level="LOW",
    required_permission="retail.view_order",
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "object"},
    handler=handle_get_order_summary,
))

ToolRegistry.register(ToolDefinition(
    name="get_service_ticket_summary",
    description="Truy vấn tổng quan các yêu cầu dịch vụ và tình trạng SLA",
    classification="READ",
    risk_level="LOW",
    required_permission="service_ops.view_servicerequest",
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "object"},
    handler=handle_get_service_ticket_summary,
))

ToolRegistry.register(ToolDefinition(
    name="get_technician_workload",
    description="Thống kê tải công việc và danh sách nhiệm vụ của kỹ thuật viên",
    classification="READ",
    risk_level="LOW",
    required_permission="service_ops.view_employee",
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "object"},
    handler=handle_get_technician_workload,
))

ToolRegistry.register(ToolDefinition(
    name="query_nearby_technicians",
    description="Tìm kiếm kỹ thuật viên gần nhất theo tọa độ địa lý GIS và khoảng cách radius",
    classification="READ",
    risk_level="LOW",
    required_permission="service_ops.view_employee",
    input_schema={"type": "object", "properties": {"ticket_id": {"type": "integer"}, "radius_km": {"type": "number"}}},
    output_schema={"type": "object"},
    handler=handle_query_nearby_technicians,
))

ToolRegistry.register(ToolDefinition(
    name="get_forecast",
    description="Truy vấn kết quả dự báo 14 ngày tới từ XGBoost ML Engine",
    classification="READ",
    risk_level="LOW",
    required_permission="forecasting.view_forecast",
    input_schema={"type": "object", "properties": {"target_type": {"type": "string"}}},
    output_schema={"type": "object"},
    handler=handle_get_forecast,
))

ToolRegistry.register(ToolDefinition(
    name="get_recommendations",
    description="Truy vấn danh sách đề xuất khuyến nghị vận hành hiện có",
    classification="READ",
    risk_level="LOW",
    required_permission="recommendations.view_recommendation",
    input_schema={"type": "object", "properties": {"status": {"type": "string"}}},
    output_schema={"type": "object"},
    handler=handle_get_recommendations,
))

# Mutation tools
ToolRegistry.register(ToolDefinition(
    name="dispatch_technician",
    description="Phân công kỹ thuật viên tiếp nhận và xử lý ticket dịch vụ",
    classification="MUTATION",
    risk_level="HIGH",
    required_permission="service_ops.change_servicerequest",
    input_schema={"type": "object", "properties": {"ticket_id": {"type": "integer"}, "employee_id": {"type": "integer"}}, "required": ["ticket_id", "employee_id"]},
    output_schema={"type": "object"},
    handler=handle_dispatch_technician,
))

ToolRegistry.register(ToolDefinition(
    name="update_order_status",
    description="Cập nhật trạng thái xử lý cho đơn hàng bán lẻ",
    classification="MUTATION",
    risk_level="MEDIUM",
    required_permission="retail.change_order",
    input_schema={"type": "object", "properties": {"order_id": {"type": "integer"}, "new_status": {"type": "string"}}, "required": ["order_id", "new_status"]},
    output_schema={"type": "object"},
    handler=handle_update_order_status,
))

ToolRegistry.register(ToolDefinition(
    name="schedule_task",
    description="Tạo và lập lịch nhiệm vụ công việc cho nhân viên dịch vụ",
    classification="MUTATION",
    risk_level="MEDIUM",
    required_permission="service_ops.add_servicetask",
    input_schema={"type": "object", "properties": {"title": {"type": "string"}, "employee_id": {"type": "integer"}}, "required": ["title"]},
    output_schema={"type": "object"},
    handler=handle_schedule_task,
))

ToolRegistry.register(ToolDefinition(
    name="create_promotion_request",
    description="Tạo đề xuất áp dụng chương trình khuyến mãi cho chi nhánh (DEPRECATED: khuyến nghị sử dụng 'adjust_product_price')",
    classification="MUTATION",
    risk_level="MEDIUM",
    required_permission="retail.change_order",
    input_schema={"type": "object", "properties": {"promotion_name": {"type": "string"}, "discount_pct": {"type": "number"}}, "required": ["promotion_name"]},
    output_schema={"type": "object"},
    handler=handle_create_promotion_request,
))

ToolRegistry.register(ToolDefinition(
    name="adjust_product_price",
    description="Điều chỉnh đơn giá niêm yết của sản phẩm bán lẻ (thay thế cho đề xuất khuyến mãi)",
    classification="MUTATION",
    risk_level="MEDIUM",
    required_permission="retail.change_product",
    input_schema={"type": "object", "properties": {"product_id": {"type": "integer"}, "new_price": {"type": "number"}}, "required": ["product_id", "new_price"]},
    output_schema={"type": "object"},
    handler=handle_adjust_product_price,
))

# Inbound Goods Receiving & Stockout Tools
def handle_get_stockout_risk_summary(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_stockout_risk_summary
    return get_stockout_risk_summary(workspace, user, **params)


def handle_get_stock_balance_summary(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_stock_balance_summary
    return get_stock_balance_summary(workspace, user, **params)


def handle_create_goods_receipt(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.retail.services import create_goods_receipt
    receipt = create_goods_receipt(workspace, user, params)
    return {
        "status": "SUCCESS",
        "receipt_id": receipt.id,
        "receipt_number": receipt.receipt_number,
        "receipt_status": receipt.status,
        "total_amount": float(receipt.total_amount),
    }


def handle_receive_goods_receipt(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.retail.models import GoodsReceipt
    from apps.retail.services import receive_goods_receipt
    receipt_id = params.get("receipt_id")
    receipt = GoodsReceipt.objects.for_workspace(workspace).filter(id=receipt_id).first()
    if not receipt:
        raise ToolValidationError(f"Goods Receipt #{receipt_id} not found in active workspace.")
    updated = receive_goods_receipt(receipt, user)
    return {
        "status": "SUCCESS",
        "receipt_id": updated.id,
        "receipt_number": updated.receipt_number,
        "receipt_status": updated.status,
    }


ToolRegistry.register(ToolDefinition(
    name="get_stockout_risk_summary",
    description="Dự báo nguy cơ hết hàng và đề xuất số lượng nhập hàng",
    classification="READ",
    risk_level="LOW",
    required_permission="retail.view_product",
    input_schema={"type": "object", "properties": {"category": {"type": "string"}, "limit": {"type": "integer"}}},
    output_schema={"type": "object"},
    handler=handle_get_stockout_risk_summary,
))

ToolRegistry.register(ToolDefinition(
    name="get_stock_balance_summary",
    description="Tra cứu tồn kho thực tế theo từng chi nhánh",
    classification="READ",
    risk_level="LOW",
    required_permission="retail.view_product",
    input_schema={"type": "object", "properties": {"category": {"type": "string"}, "branch_id": {"type": "integer"}}},
    output_schema={"type": "object"},
    handler=handle_get_stock_balance_summary,
))

ToolRegistry.register(ToolDefinition(
    name="create_goods_receipt",
    description="Tạo phiếu nhập hàng mới vào kho chi nhánh",
    classification="MUTATION",
    risk_level="HIGH",
    required_permission="retail.add_goodsreceipt",
    input_schema={"type": "object", "properties": {"supplier_id": {"type": "integer"}, "branch_id": {"type": "integer"}, "items": {"type": "array"}}, "required": ["supplier_id", "branch_id", "items"]},
    output_schema={"type": "object"},
    handler=handle_create_goods_receipt,
))

ToolRegistry.register(ToolDefinition(
    name="receive_goods_receipt",
    description="Xác nhận nhập kho phiếu hàng và tăng tồn kho thực tế",
    classification="MUTATION",
    risk_level="CRITICAL",
    required_permission="retail.change_goodsreceipt",
    input_schema={"type": "object", "properties": {"receipt_id": {"type": "integer"}}, "required": ["receipt_id"]},
    output_schema={"type": "object"},
    handler=handle_receive_goods_receipt,
))


# -------------------------------------------------------------------------
# NEW BUSINESS ANALYTICS TOOLS REGISTRATIONS
# -------------------------------------------------------------------------

def handle_compare_entities_analytics(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import compare_entities_analytics
    return compare_entities_analytics(workspace, user, **params)


def handle_get_sales_trend_analytics(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_sales_trend_analytics
    return get_sales_trend_analytics(workspace, user, **params)


def handle_get_service_labor_cost_summary(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_service_labor_cost_summary
    return get_service_labor_cost_summary(workspace, user, **params)


def handle_get_service_catalog_summary(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_service_catalog_summary
    return get_service_catalog_summary(workspace, user, **params)


ToolRegistry.register(ToolDefinition(
    name="compare_entities_analytics",
    description="So sánh doanh số, doanh thu giữa các sản phẩm, thương hiệu hoặc chi nhánh",
    classification="READ",
    risk_level="LOW",
    required_permission="retail.view_order",
    input_schema={"type": "object", "properties": {"entity_type": {"type": "string"}, "entities": {"type": "array"}, "metric": {"type": "string"}}},
    output_schema={"type": "object"},
    handler=handle_compare_entities_analytics,
))

ToolRegistry.register(ToolDefinition(
    name="get_sales_trend_analytics",
    description="Phân tích xu hướng tăng trưởng, sụt giảm doanh số chuỗi thời gian",
    classification="READ",
    risk_level="LOW",
    required_permission="retail.view_order",
    input_schema={"type": "object", "properties": {"category": {"type": "string"}, "period_days": {"type": "integer"}}},
    output_schema={"type": "object"},
    handler=handle_get_sales_trend_analytics,
))

ToolRegistry.register(ToolDefinition(
    name="get_service_labor_cost_summary",
    description="Thống kê tổng giờ công và chi phí nhân công kỹ thuật viên",
    classification="READ",
    risk_level="LOW",
    required_permission="service.view_request",
    input_schema={"type": "object", "properties": {"ticket_id": {"type": "integer"}, "employee_id": {"type": "integer"}}},
    output_schema={"type": "object"},
    handler=handle_get_service_labor_cost_summary,
))

ToolRegistry.register(ToolDefinition(
    name="get_service_catalog_summary",
    description="Tra cứu danh mục dịch vụ IT, bảng giá và thời gian xử lý tiêu chuẩn",
    classification="READ",
    risk_level="LOW",
    required_permission="service.view_service",
    input_schema={"type": "object", "properties": {"category": {"type": "string"}}},
    output_schema={"type": "object"},
    handler=handle_get_service_catalog_summary,
))


def handle_get_customer_order_history(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_customer_order_history
    return get_customer_order_history(workspace, user, **params)


def handle_get_technician_skills_summary(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_technician_skills_summary
    return get_technician_skills_summary(workspace, user, **params)


def handle_get_technician_schedule_summary(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_technician_schedule_summary
    return get_technician_schedule_summary(workspace, user, **params)


def handle_simulate_what_if_scenario(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import simulate_what_if_scenario
    return simulate_what_if_scenario(workspace, user, **params)


def handle_explain_root_cause(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import explain_root_cause
    return explain_root_cause(workspace, user, **params)


def handle_get_spatial_ticket_clusters(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_spatial_ticket_clusters
    return get_spatial_ticket_clusters(workspace, user, **params)


ToolRegistry.register(ToolDefinition(
    name="get_customer_order_history",
    description="Tra cứu lịch sử mua hàng, danh sách đơn và tổng chi tiêu của khách hàng",
    classification="READ",
    risk_level="LOW",
    required_permission="retail.view_order",
    input_schema={"type": "object", "properties": {"customer_name": {"type": "string"}}},
    output_schema={"type": "object"},
    handler=handle_get_customer_order_history,
))

ToolRegistry.register(ToolDefinition(
    name="get_technician_skills_summary",
    description="Tìm kiếm kỹ thuật viên theo kỹ năng chuyên môn và trạng thái sẵn sàng",
    classification="READ",
    risk_level="LOW",
    required_permission="service.view_employee",
    input_schema={"type": "object", "properties": {"skill": {"type": "string"}, "is_available_only": {"type": "boolean"}}},
    output_schema={"type": "object"},
    handler=handle_get_technician_skills_summary,
))

ToolRegistry.register(ToolDefinition(
    name="get_technician_schedule_summary",
    description="Tra cứu lịch làm việc và phát hiện xung đột trùng lịch kỹ thuật viên",
    classification="READ",
    risk_level="LOW",
    required_permission="service.view_schedule",
    input_schema={"type": "object", "properties": {"date_target": {"type": "string"}, "conflict_check": {"type": "boolean"}}},
    output_schema={"type": "object"},
    handler=handle_get_technician_schedule_summary,
))

ToolRegistry.register(ToolDefinition(
    name="simulate_what_if_scenario",
    description="Mô phỏng kịch bản giả định định lượng (What-If simulation)",
    classification="READ",
    risk_level="LOW",
    required_permission="retail.view_order",
    input_schema={"type": "object", "properties": {"scenario_type": {"type": "string"}, "change_pct": {"type": "number"}}},
    output_schema={"type": "object"},
    handler=handle_simulate_what_if_scenario,
))

ToolRegistry.register(ToolDefinition(
    name="explain_root_cause",
    description="Phân tích và giải thích nguyên nhân gốc rễ cảnh báo hoặc đề xuất",
    classification="READ",
    risk_level="LOW",
    required_permission="service.view_request",
    input_schema={"type": "object", "properties": {"target_type": {"type": "string"}}},
    output_schema={"type": "object"},
    handler=handle_explain_root_cause,
))

ToolRegistry.register(ToolDefinition(
    name="get_spatial_ticket_clusters",
    description="Phân tích mật độ và điểm nóng tập trung sự cố theo không gian GIS",
    classification="READ",
    risk_level="LOW",
    required_permission="service.view_request",
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "object"},
    handler=handle_get_spatial_ticket_clusters,
))


# -------------------------------------------------------------------------
# PHASE 2 ENTERPRISE TOOLS REGISTRATIONS
# -------------------------------------------------------------------------

def handle_create_stock_transfer(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.retail.services import execute_stock_transfer
    transfer = execute_stock_transfer(workspace, user, params)
    return {
        "status": "SUCCESS",
        "transfer_id": transfer.id,
        "reference_number": transfer.reference_number,
        "source_branch_id": transfer.source_branch_id,
        "destination_branch_id": transfer.destination_branch_id,
        "product_id": transfer.product_id,
        "quantity": transfer.quantity,
        "transfer_status": transfer.status,
    }


def handle_get_category_profit_margins(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_category_profit_margins
    return get_category_profit_margins(workspace, user, **params)


def handle_get_customer_churn_risk_summary(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_customer_churn_risk_summary
    return get_customer_churn_risk_summary(workspace, user, **params)


def handle_get_inter_branch_transfer_recommendations(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_inter_branch_transfer_recommendations
    return get_inter_branch_transfer_recommendations(workspace, user, **params)


def handle_get_technician_safety_compliance(workspace: Workspace, user: User, params: Dict[str, Any]) -> Dict[str, Any]:
    from apps.knowledge.tools import get_technician_safety_compliance
    return get_technician_safety_compliance(workspace, user, **params)


ToolRegistry.register(ToolDefinition(
    name="create_stock_transfer",
    description="Tạo lệnh điều chuyển hàng hóa giữa các chi nhánh nội bộ",
    classification="MUTATION",
    risk_level="HIGH",
    required_permission="retail.change_product",
    input_schema={"type": "object", "properties": {"source_branch_id": {"type": "integer"}, "destination_branch_id": {"type": "integer"}, "product_id": {"type": "integer"}, "quantity": {"type": "integer"}}, "required": ["source_branch_id", "destination_branch_id", "product_id", "quantity"]},
    output_schema={"type": "object"},
    handler=handle_create_stock_transfer,
))

ToolRegistry.register(ToolDefinition(
    name="get_category_profit_margins",
    description="Phân tích doanh thu, giá vốn và biên lợi nhuận gộp theo danh mục sản phẩm",
    classification="READ",
    risk_level="LOW",
    required_permission="retail.view_order",
    input_schema={"type": "object", "properties": {"category": {"type": "string"}}},
    output_schema={"type": "object"},
    handler=handle_get_category_profit_margins,
))

ToolRegistry.register(ToolDefinition(
    name="get_customer_churn_risk_summary",
    description="Rà soát khách hàng VIP và doanh nghiệp có nguy cơ rời bỏ",
    classification="READ",
    risk_level="LOW",
    required_permission="retail.view_customer",
    input_schema={"type": "object", "properties": {"inactivity_days": {"type": "integer"}}},
    output_schema={"type": "object"},
    handler=handle_get_customer_churn_risk_summary,
))

ToolRegistry.register(ToolDefinition(
    name="get_inter_branch_transfer_recommendations",
    description="Khuyến nghị điều chuyển tồn kho cân đối giữa các chi nhánh",
    classification="READ",
    risk_level="LOW",
    required_permission="retail.view_stock",
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "object"},
    handler=handle_get_inter_branch_transfer_recommendations,
))

ToolRegistry.register(ToolDefinition(
    name="get_technician_safety_compliance",
    description="Đánh giá ma trận chứng chỉ, định mức tải và tuân thủ an toàn giờ làm thêm",
    classification="READ",
    risk_level="LOW",
    required_permission="service.view_technician",
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "object"},
    handler=handle_get_technician_safety_compliance,
))
