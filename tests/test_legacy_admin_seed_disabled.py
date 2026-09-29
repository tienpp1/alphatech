from io import StringIO
from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, override_settings


class LegacyAdminSeedDisabledTests(SimpleTestCase):
    # SimpleTestCase disallows DB queries: rejection must happen before any write/read.
    def test_disabled_in_every_environment_without_database_access(self):
        for debug in (True, False):
            with self.subTest(debug=debug), override_settings(DEBUG=debug):
                output = StringIO()
                with self.assertRaisesMessage(CommandError, 'đã bị vô hiệu hóa'):
                    call_command('seed_student_admin', stdout=output)
                self.assertNotIn('success', output.getvalue().lower())
