from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.utils import timezone
from django.db import transaction
from apps.workspaces.models import Workspace
from apps.retail.models import Customer, Order
from apps.service_ops.models import Service, ServiceRequest
from apps.notifications.models import Notification


class CustomerApprovalNoticeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='celebrate',email='celebrate@example.test',password='test-password-123')
        cls.other = get_user_model().objects.create_user(username='other-celebrate',email='other-celebrate@example.test',password='test-password-123')
        cls.ws = Workspace.objects.create(code='celebrate-retail',name='Retail',workspace_type='RETAIL')
        cls.customer = Customer.objects.create(workspace=cls.ws,user=cls.user,code='c1',name='Customer')
        cls.service_ws = Workspace.objects.create(code='celebrate-service',name='Service',workspace_type='SERVICE')
        cls.service_customer = Customer.objects.create(workspace=cls.service_ws,user=cls.user,code='c2',name='Customer')
        cls.service = Service.objects.create(workspace=cls.service_ws,code='svc',name='Repair')

    def order(self):
        return Order.objects.create(workspace=self.ws,customer=self.customer,created_by=self.user,order_number='CELEBRATE-1',order_date=timezone.localdate(),order_timestamp=timezone.now())

    def test_order_emits_only_after_approval_once(self):
        order = self.order()
        self.assertFalse(Notification.objects.filter(event_type='CUSTOMER_ORDER_APPROVED').exists())
        order.status='CONFIRMED'; order.save()
        order.save()
        self.assertEqual(Notification.objects.filter(event_type='CUSTOMER_ORDER_APPROVED',recipient=self.user).count(),1)
        self.client.force_login(self.user)
        response=self.client.get('/tai-khoan/thong-bao-duyet/')
        self.assertEqual(len(response.json()['notifications']),1)
        notice_id=response.json()['notifications'][0]['id']
        self.assertEqual(self.client.post(f'/tai-khoan/thong-bao-duyet/{notice_id}/da-xem/').status_code,200)
        self.assertEqual(self.client.get('/tai-khoan/thong-bao-duyet/').json()['notifications'],[])

    def test_cross_user_and_csrf_denied(self):
        order=self.order(); order.status='CONFIRMED'; order.save()
        notice=Notification.objects.get(event_type='CUSTOMER_ORDER_APPROVED')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get('/tai-khoan/thong-bao-duyet/').json()['notifications'],[])
        self.assertEqual(self.client.post(f'/tai-khoan/thong-bao-duyet/{notice.pk}/da-xem/').status_code,404)
        csrf=Client(enforce_csrf_checks=True); csrf.force_login(self.user)
        self.assertEqual(csrf.post(f'/tai-khoan/thong-bao-duyet/{notice.pk}/da-xem/').status_code,403)

    def test_cancelled_or_reassigned_order_does_not_celebrate(self):
        order=self.order(); order.status='CONFIRMED'; order.save()
        order.status='CANCELLED'; order.save()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/tai-khoan/thong-bao-duyet/').json()['notifications'],[])

    def test_service_acceptance_and_repeated_save(self):
        item=ServiceRequest.objects.create(workspace=self.service_ws,customer=self.service_customer,service=self.service,request_number='SVC-1',title='Repair',description='Test')
        item.status='ASSIGNED'; item.save()
        item.status='IN_PROGRESS'; item.save()
        self.assertEqual(Notification.objects.filter(event_type='CUSTOMER_SERVICE_APPROVED',recipient=self.user).count(),1)

    def test_rollback_removes_notice(self):
        order=self.order()
        try:
            with transaction.atomic():
                order.status='CONFIRMED'; order.save()
                raise ValueError('rollback')
        except ValueError:
            pass
        self.assertFalse(Notification.objects.filter(event_type='CUSTOMER_ORDER_APPROVED').exists())

    def test_anonymous_denied(self):
        self.assertEqual(self.client.get('/tai-khoan/thong-bao-duyet/').status_code,401)
