"""Saved forecasts feed advisory rules, never fake current facts or actions."""
import copy
import datetime
from decimal import Decimal

from concurrent.futures import ThreadPoolExecutor
import threading

from django.db import connections, close_old_connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Permission, Role, User
from apps.approvals.models import ApprovalRequest
from apps.forecasting.models import ForecastModelConfig, ForecastResult, ForecastRun
from apps.recommendations.models import Recommendation
from apps.recommendations.rules import evaluate_retail_recommendations
from apps.recommendations.services import accept_recommendation, recommendation_review_state
from apps.approvals.registry import ToolValidationError
from apps.retail.models import Customer, Order
from apps.workspaces.models import Workspace, WorkspaceMembership


class ForecastBackedRecommendationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.workspace = Workspace.objects.create(code='forecast-rule', name='Retail', workspace_type='RETAIL')
        cls.other = Workspace.objects.create(code='forecast-rule-other', name='Other', workspace_type='RETAIL')
        cls.customer = Customer.objects.create(workspace=cls.workspace, code='FC', name='TEST')
        cls.user = User.objects.create_user(username='forecast-rule-manager', email='fcr@example.invalid', password='test-only')
        role = Role.objects.create(name='MANAGER')
        for code in ('recommendations.manage_recommendation', 'recommendations.view_recommendation'):
            permission, _ = Permission.objects.get_or_create(codename=code, defaults={'name': code, 'module': 'recommendations'})
            role.permissions.add(permission)
        WorkspaceMembership.objects.create(user=cls.user, workspace=cls.workspace, role=role, is_default=True)
        cls.end = timezone.localdate()
        cls.config = ForecastModelConfig.objects.create(
            workspace=cls.workspace, name='Guarded revenue', target_type='RETAIL_REVENUE',
            granularity='DAILY', training_config={'strategy': 'guarded_direct_v1'},
        )
        cls.forecast_run = ForecastRun.objects.create(
            workspace=cls.workspace, model_config=cls.config, target_type='RETAIL_REVENUE',
            status='COMPLETED', dataset_period_start=cls.end-datetime.timedelta(days=125),
            dataset_period_end=cls.end, dataset_row_count=126, test_row_count=28,
            model_metrics={'mae': 5, 'rmse': 6, 'r2': -0.5},
            job_parameters={'dimensions': {}, 'provenance': {
                'workspace_code': cls.workspace.code, 'target_type': 'RETAIL_REVENUE',
                'model_config_id': cls.config.pk, 'model_version': 1,
                'granularity': 'DAILY', 'dimensions': {}, 'strategy': 'guarded_direct_v1',
                'effective_model': 'MA7', 'deployment_qualification': True,
                'dataset': {'period_start': (cls.end-datetime.timedelta(days=125)).isoformat(),
                            'period_end': cls.end.isoformat(), 'fingerprint_sha256': '1'*64},
                'evaluation': {'counts': {'observed_holdout': 20, 'holdout': 28}},
            }},
        )
        for index in range(1, 8):
            ForecastResult.objects.create(workspace=cls.workspace, forecast_run=cls.forecast_run,
                target_type='RETAIL_REVENUE', forecast_date=cls.end+datetime.timedelta(days=index),
                predicted_value=70, actual_value=99999)
        for index in range(7):
            Order.objects.create(workspace=cls.workspace, customer=cls.customer,
                order_number=f'FORECAST-BASE-{index}', order_date=cls.end-datetime.timedelta(days=index),
                order_timestamp=timezone.now(), status='COMPLETED', total_amount=100)

    def forecast_recs(self):
        return Recommendation.objects.filter(workspace=self.workspace, supporting_data__forecast_run_id=self.forecast_run.pk)

    def evaluate_api(self, payload=None):
        client = APIClient()
        client.force_authenticate(self.user)
        return client.post('/api/v1/recommendations/evaluate/', payload or {}, format='json',
                           HTTP_X_WORKSPACE_ID=str(self.workspace.pk))

    def alter_provenance(self, **values):
        params = copy.deepcopy(self.forecast_run.job_parameters)
        params['provenance'].update(values)
        self.forecast_run.job_parameters = params
        self.forecast_run.save(update_fields=['job_parameters'])

    def make_historical(self):
        old_end = self.end-datetime.timedelta(days=40)
        offset = self.end-old_end
        self.forecast_run.dataset_period_end = old_end
        self.forecast_run.dataset_period_start -= offset
        params = copy.deepcopy(self.forecast_run.job_parameters)
        params['provenance']['dataset'].update(period_start=self.forecast_run.dataset_period_start.isoformat(), period_end=old_end.isoformat())
        self.forecast_run.job_parameters = params
        self.forecast_run.save()
        for point in self.forecast_run.results.all():
            point.forecast_date -= offset
            point.save(update_fields=['forecast_date'])
        for order in Order.objects.filter(workspace=self.workspace):
            order.order_date -= offset
            order.save(update_fields=['order_date'])

    def test_actual_saved_model_predictions_and_completed_order_baseline_produce_advice(self):
        evaluate_retail_recommendations(self.workspace)
        self.assertEqual(self.forecast_recs().count(), 1)
        rec = self.forecast_recs().get()
        evidence = rec.supporting_data
        self.assertEqual(evidence['forecast_total'], 490)
        self.assertEqual(evidence['observed_total'], 700)
        self.assertEqual(evidence['predicted_change_pct'], -30)
        self.assertEqual(evidence['model'], 'MA7')
        self.assertEqual(evidence['baseline_source'], 'canonical_completed_orders_at_evaluation')
        self.assertEqual(evidence['analysis_mode'], 'CURRENT_SNAPSHOT')
        self.assertEqual(len(evidence['forecast_result_ids']), 7)
        self.assertIn(f'forecast_run:{self.forecast_run.pk}', rec.source_references)
        self.assertEqual(rec.proposed_action, '')
        self.assertIsNone(rec.approval_request_id)
        self.assertIn('R²', rec.explanation['why'])
        self.assertFalse(ApprovalRequest.objects.exists())

    def test_threshold_is_strictly_more_than_ten_percent(self):
        self.forecast_run.results.update(predicted_value=90)
        evaluate_retail_recommendations(self.workspace)
        self.assertFalse(self.forecast_recs().exists())

    def test_current_rule_does_not_claim_past_horizon_is_upcoming(self):
        self.make_historical()
        evaluate_retail_recommendations(self.workspace)
        self.assertFalse(self.forecast_recs().exists())

    def test_explicit_historical_api_analysis_is_labeled_and_cannot_be_accepted(self):
        self.make_historical()
        response = self.evaluate_api({'include_historical_forecast': True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.forecast_recs().count(), 1)
        rec = self.forecast_recs().get()
        self.assertEqual(rec.supporting_data['analysis_mode'], 'HISTORICAL')
        self.assertIn('lịch sử', rec.title.lower())
        self.assertTrue(recommendation_review_state(rec)['stale'])
        with self.assertRaises(ToolValidationError):
            accept_recommendation(rec, self.user)
        self.assertFalse(ApprovalRequest.objects.exists())

    def test_repeated_evaluation_keeps_first_evidence_even_if_canonical_orders_change(self):
        evaluate_retail_recommendations(self.workspace)
        self.assertEqual(self.forecast_recs().count(), 1)
        before = self.forecast_recs().get().supporting_data
        Order.objects.filter(workspace=self.workspace).update(total_amount=500)
        evaluate_retail_recommendations(self.workspace)
        self.assertEqual(self.forecast_recs().count(), 1)
        self.assertEqual(self.forecast_recs().get().supporting_data, before)

    def test_incomplete_week_is_not_filled_as_observed_zero_revenue(self):
        Order.objects.filter(workspace=self.workspace, order_date=self.end-datetime.timedelta(days=3)).update(status='PENDING')
        evaluate_retail_recommendations(self.workspace)
        self.assertFalse(self.forecast_recs().exists())

    def test_missing_forecast_day_is_not_patched_with_actual_value(self):
        self.forecast_run.results.filter(forecast_date=self.end+datetime.timedelta(days=4)).delete()
        evaluate_retail_recommendations(self.workspace)
        self.assertFalse(self.forecast_recs().exists())

    def test_foreign_or_wrong_target_result_is_not_a_valid_prediction_week(self):
        point = self.forecast_run.results.first()
        for field, value in (('workspace', self.other), ('target_type', 'RETAIL_ORDER_VOLUME')):
            with self.subTest(field=field):
                original = getattr(point, field)
                setattr(point, field, value)
                point.save(update_fields=[field])
                evaluate_retail_recommendations(self.workspace)
                self.assertFalse(self.forecast_recs().exists())
                setattr(point, field, original)
                point.save(update_fields=[field])

    def test_latest_bad_run_never_falls_back_to_older_good_run(self):
        newer = ForecastRun.objects.create(workspace=self.workspace, model_config=self.config,
            target_type='RETAIL_REVENUE', status='FAILED')
        for state in ('FAILED', 'PENDING', 'RUNNING', 'CANCELLED'):
            newer.status = state
            newer.save(update_fields=['status'])
            evaluate_retail_recommendations(self.workspace)
            self.assertFalse(self.forecast_recs().exists())

    def test_new_active_config_without_run_does_not_reuse_disabled_model(self):
        ForecastModelConfig.objects.create(workspace=self.workspace, name='New config',
            target_type='RETAIL_REVENUE', model_version=2)
        evaluate_retail_recommendations(self.workspace)
        self.assertFalse(self.forecast_recs().exists())

    def test_invalid_provenance_never_becomes_authoritative_forecast_advice(self):
        original = copy.deepcopy(self.forecast_run.job_parameters)
        variants = (
            {'workspace_code': self.other.code}, {'target_type': 'SERVICE_TICKET_VOLUME'},
            {'model_config_id': self.config.pk+1000}, {'granularity': 'WEEKLY'},
            {'dimensions': {'branch_id': 1}}, {'effective_model': 'UNKNOWN'},
            {'deployment_qualification': False}, {'deployment_qualification': 'true'},
            {'evaluation': {'counts': {'observed_holdout': 2, 'holdout': 28}}},
            {'evaluation': {'counts': {'observed_holdout': True, 'holdout': 28}}},
            {'evaluation': {'counts': {'observed_holdout': 29, 'holdout': 28}}},
            {'dataset': {'period_end': '2020-01-01', 'fingerprint_sha256': '1'*64}},
        )
        for delta in variants:
            with self.subTest(delta=delta):
                self.forecast_run.job_parameters = copy.deepcopy(original)
                self.alter_provenance(**delta)
                evaluate_retail_recommendations(self.workspace)
                self.assertFalse(self.forecast_recs().exists())

    def test_historical_opt_in_does_not_bypass_holdout_quality_guard(self):
        self.make_historical()
        self.alter_provenance(evaluation={'counts': {'observed_holdout': 2, 'holdout': 28}})
        self.assertEqual(self.evaluate_api({'include_historical_forecast': True}).status_code, 200)
        self.assertFalse(self.forecast_recs().exists())

    def test_bad_opt_in_payload_is_rejected_before_rule_writes(self):
        for payload in ([], {'include_historical_forecast': 'yes'}, {'include_historical_forecast': 1}):
            client = APIClient()
            client.force_authenticate(self.user)
            response = client.post('/api/v1/recommendations/evaluate/', payload, format='json',
                                   HTTP_X_WORKSPACE_ID=str(self.workspace.pk))
            self.assertEqual(response.status_code, 400)
        self.assertFalse(Recommendation.objects.exists())

    def test_foreign_workspace_evaluation_is_denied(self):
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post('/api/v1/recommendations/evaluate/', {}, format='json',
                              HTTP_X_WORKSPACE_ID=str(self.other.pk))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Recommendation.objects.exists())

    def test_future_source_is_not_permitted_even_in_historical_mode(self):
        self.forecast_run.dataset_period_end = self.end+datetime.timedelta(days=1)
        self.forecast_run.save(update_fields=['dataset_period_end'])
        self.alter_provenance(dataset={'period_end': self.forecast_run.dataset_period_end.isoformat(),
                                       'fingerprint_sha256': '1'*64})
        self.assertEqual(self.evaluate_api({'include_historical_forecast': True}).status_code, 200)
        self.assertFalse(self.forecast_recs().exists())

    def test_zero_or_negative_totals_are_not_a_decline_denominator(self):
        for amount in (0, -100):
            Order.objects.filter(workspace=self.workspace).update(total_amount=amount)
            evaluate_retail_recommendations(self.workspace)
            self.assertFalse(self.forecast_recs().exists())

    def test_actual_mae_and_rmse_must_be_measured_numbers_not_text_or_flags(self):
        for invalid in ('5', True, None, -1):
            with self.subTest(invalid=invalid):
                self.forecast_run.model_metrics = {'mae': invalid, 'rmse': 6, 'r2': -0.5}
                self.forecast_run.save(update_fields=['model_metrics'])
                evaluate_retail_recommendations(self.workspace)
                self.assertFalse(self.forecast_recs().exists())

    def test_invalid_latest_configuration_shape_fails_closed_not_500(self):
        self.config.training_config = ['not-a-config']
        self.config.save(update_fields=['training_config'])
        self.alter_provenance(strategy=None)
        evaluate_retail_recommendations(self.workspace)
        self.assertFalse(self.forecast_recs().exists())

    def test_negative_prediction_and_missing_provenance_do_not_create_advice(self):
        point = self.forecast_run.results.first()
        point.predicted_value = -1
        point.save(update_fields=['predicted_value'])
        evaluate_retail_recommendations(self.workspace)
        self.assertFalse(self.forecast_recs().exists())
        point.predicted_value = 70
        point.save(update_fields=['predicted_value'])
        self.forecast_run.job_parameters = {}
        self.forecast_run.save(update_fields=['job_parameters'])
        evaluate_retail_recommendations(self.workspace)
        self.assertFalse(self.forecast_recs().exists())


class ForecastRecommendationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        ForecastBackedRecommendationTests.setUpTestData.__func__(type(self))

    def test_two_evaluators_create_only_one_forecast_advice(self):
        from apps.recommendations.forecast_rules import evaluate_forecast_recommendations
        gate = threading.Barrier(2, timeout=10)
        workspace_id = self.workspace.pk

        def evaluate():
            close_old_connections()
            try:
                local_workspace = Workspace.objects.get(pk=workspace_id)
                gate.wait()
                return len(evaluate_forecast_recommendations(local_workspace))
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda unused: evaluate(), range(2)))
        self.assertEqual(sorted(results), [0, 1])
        self.assertEqual(Recommendation.objects.filter(workspace_id=workspace_id,
            supporting_data__forecast_run_id=self.forecast_run.pk).count(), 1)
