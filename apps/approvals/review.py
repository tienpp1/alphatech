"""Derived review eligibility. Reads never expire or rewrite saved history."""
import datetime
from django.utils import timezone
from apps.approvals.models import ApprovalStatus
from apps.approvals.registry import ToolRegistry, ToolValidationError, validate_action_contract


def validate_approval_current(approval, *, lock=False):
    from apps.approvals.executor import _check_user_tool_permission
    from apps.recommendations.models import Recommendation, RecommendationStatus
    from apps.recommendations.services import recommendation_review_state
    tool = ToolRegistry.get(approval.proposed_action)
    if tool is None or tool.classification != 'MUTATION':
        raise ToolValidationError('Hành động không còn là contract thay đổi hợp lệ; cần lập yêu cầu mới.')
    if not _check_user_tool_permission(approval.requester, approval.workspace, tool.required_permission):
        raise ToolValidationError('Người yêu cầu không còn quyền thực hiện hành động trong workspace.')
    if approval.created_at <= timezone.now()-datetime.timedelta(days=7):
        raise ToolValidationError('Yêu cầu đã cũ quá 7 ngày; cần đánh giá và lập lại.')
    recommendations = Recommendation.objects.filter(approval_request_id=approval.pk)
    if lock:
        recommendations = recommendations.select_for_update()
    source = recommendations.first()
    if source:
        if (source.workspace_id != approval.workspace_id or source.status != RecommendationStatus.ACCEPTED
                or source.proposed_action != approval.proposed_action or source.proposed_parameters != approval.parameters):
            raise ToolValidationError('Khuyến nghị liên kết đã đổi hoặc không khớp workspace/tham số hành động.')
        state = recommendation_review_state(source)
        if state['stale']:
            raise ToolValidationError(state['label'])
    validate_action_contract(tool, approval.workspace, approval.parameters)
    return tool


def approval_review_state(approval):
    if approval.status != ApprovalStatus.PENDING:
        return {'current': False, 'stale': False, 'label': 'Lịch sử quyết định — không thực thi lại.'}
    try:
        validate_approval_current(approval)
    except ToolValidationError as exc:
        return {'current': False, 'stale': True, 'label': str(exc)}
    return {'current': True, 'stale': False, 'label': 'Cần người độc lập phê duyệt; điều kiện sẽ được kiểm tra lại trước thực thi.'}


def review_queue(rows, state_fn, queue='current'):
    result = []
    for row in rows:
        row.review_state = state_fn(row)
        current = row.review_state['current']
        if queue == 'all' or (queue == 'history' and not current) or (queue not in ('all', 'history') and current):
            result.append(row)
    return result
