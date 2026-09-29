"""Disabled legacy bootstrap: never reset passwords or promote fixed identities."""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Disabled unsafe legacy admin bootstrap. Use explicit account administration.'
    requires_system_checks = []
    requires_migrations_checks = False

    def handle(self, *args, **options):
        raise CommandError(
            'Lệnh seed_student_admin đã bị vô hiệu hóa vì dùng mật khẩu cố định '
            'và tự nâng quyền tài khoản. Không có dữ liệu nào được thay đổi. '
            'Nếu cần tạo quản trị viên mới, dùng createsuperuser tương tác; '
            'việc cấp quyền workspace phải được quản trị riêng theo nhu cầu.'
        )
