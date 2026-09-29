"""Real database enforcement evidence, not model-method mocks."""
from django.db import connection, DatabaseError, transaction
from django.test import TestCase
from apps.audit.models import AuditLog


class AuditDatabaseEvidenceTests(TestCase):
    def setUp(self):
        self.assertEqual(connection.vendor, 'postgresql', 'This evidence requires PostgreSQL, not SQLite.')
        self.row = AuditLog.objects.create(action='EVIDENCE', entity_type='Test', entity_id='1')

    def test_raw_update_is_rejected(self):
        with self.assertRaisesMessage(DatabaseError, 'append-only'), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('UPDATE audit_auditlog SET action = %s WHERE id = %s', ['ALTERED', self.row.pk])
        self.row.refresh_from_db()
        self.assertEqual(self.row.action, 'EVIDENCE')

    def test_raw_delete_is_rejected(self):
        with self.assertRaisesMessage(DatabaseError, 'append-only'), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM audit_auditlog WHERE id = %s', [self.row.pk])
        self.assertTrue(AuditLog.objects.filter(pk=self.row.pk).exists())
