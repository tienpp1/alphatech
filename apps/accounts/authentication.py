from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import PermissionDenied
from apps.accounts.internal_access import has_internal_role


class InternalTokenAuthentication(TokenAuthentication):
    """Tokens are issued by password login; role revocation applies immediately."""
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if not has_internal_role(user):
            raise PermissionDenied("Tài khoản không có quyền truy cập nội bộ.")
        return user, token
