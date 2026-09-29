"""Bounded mechanical edit of silent mutation failures; preserves other functions."""
from pathlib import Path
p = Path(__file__).resolve().parents[1] / 'apps/knowledge/services.py'
text = p.read_text(encoding='utf-8')
text = text.replace('import os\n', 'import os\nimport logging\n', 1)
text = text.replace('FALLBACK_NO_CONTEXT_MESSAGE =', 'logger = logging.getLogger(__name__)\n\nFALLBACK_NO_CONTEXT_MESSAGE =', 1)
start = text.index('def detect_and_handle_mutation_request(')
end = text.index('def _call_gemini_chat_api(', start)
part = text[start:end]
assert part.count('except Exception:\n') == 6
for indent in ('            ', '        '):
    old = indent + 'except Exception:\n' + indent + '    pass'
    new = indent + 'except Exception:\n' + indent + "    logger.warning('MUTATION_REQUEST_FAILED')\n" + indent + '    raise'
    part = part.replace(old, new)
text = text[:start] + part + text[end:]
start = text.index('def _call_gemini_chat_api(')
end = text.index('def generate_grounded_answer(', start)
part = text[start:end].replace('except Exception:\n        pass', "except Exception:\n        logger.warning('GEMINI_GENERATION_UNAVAILABLE')\n        return None")
text = text[:start] + part + text[end:]
start = text.index('    except Exception as e:\n        answer_text = f"Không thể tạo yêu cầu thay đổi:')
end = text.index('    # 5. Hybrid Question Routing', start)
part = text[start:end]
part = part.replace('        answer_text = f"Không thể tạo yêu cầu thay đổi: {str(e)}"', '''        from apps.approvals.registry import ToolPermissionDenied as ApprovalPermissionDenied
        from django.core.exceptions import PermissionDenied
        denied = isinstance(e, (ApprovalPermissionDenied, ToolPermissionDenied, PermissionDenied))
        error_code = 'PERMISSION_DENIED' if denied else 'MUTATION_FAILED'
        answer_text = ('Bạn không có quyền thực hiện yêu cầu thay đổi này.' if denied
                       else 'Không thể tạo yêu cầu thay đổi. Vui lòng kiểm tra thông tin và thử lại.')
        logger.warning('AI_MUTATION_REJECTED code=%s', error_code)''')
part = part.replace('str(e)', 'error_code')
text = text[:start] + part + text[end:]
p.write_text(text, encoding='utf-8')
print('Six mutation handlers preserve failure; user-facing errors sanitized.')
