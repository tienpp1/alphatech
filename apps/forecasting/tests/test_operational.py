"""Synthetic, isolated fixtures for readiness; not commercial provenance evidence."""
import datetime as dt
import tempfile
import hashlib
from copy import deepcopy
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch

import numpy as np
import pandas as pd
from django.test import SimpleTestCase, TestCase, override_settings
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.retail.models import Customer, Order, OrderStatus, Category, Product
from apps.forecasting import selectors, services
from apps.forecasting.diagnostics import assess_snapshot
from apps.forecasting.evaluation import compute_metrics
from apps.forecasting.guarded import fit_guarded
from apps.forecasting.models import ForecastModelConfig, ForecastRun, ForecastResult, TargetType
from apps.forecasting.serializers import ForecastRunSerializer, TrainForecastRequestSerializer


TODAY = dt.date(2026, 11, 17)  # Tuesday: last closed W-MON ends November 16.


class OperationalPureTests(SimpleTestCase):
    @patch('apps.forecasting.diagnostics.timezone.localdate', return_value=TODAY)
    def test_today_source_is_open_not_closed_operational_evidence(self, _):
        result = assess_snapshot(TODAY, [TODAY + dt.timedelta(days=1)])
        self.assertEqual(result['status'], 'OPEN_PERIOD')
        self.assertFalse(result['operational'])

    @patch('apps.forecasting.diagnostics.timezone.localdate', return_value=TODAY)
    def test_mixed_elapsed_and_future_points_do_not_make_source_historical(self, _):
        result = assess_snapshot(dt.date(2026, 11, 15),
                                 [dt.date(2026, 11, 16), TODAY, dt.date(2026, 11, 18)])
        self.assertEqual(result['status'], 'CURRENT_SNAPSHOT')
        self.assertEqual(result['horizon_status'], 'MIXED')
        self.assertEqual(result['elapsed_point_count'], 1)
        self.assertEqual(result['upcoming_point_count'], 2)

    def test_metric_denominators_expose_zero_exclusion_without_replacing_old_scores(self):
        result = compute_metrics(np.array([0., 10., 20.]), np.array([5., 15., 10.]))
        self.assertEqual(result['mape'], 50.)
        self.assertAlmostEqual(result['wape'], 66.666667, places=5)
        self.assertEqual(result['mape_denominator_count'], 2)
        self.assertEqual(result['scored_count'], 3)
        self.assertIsNone(compute_metrics(np.array([0.]), np.array([5.]))['wape'])

    def test_guarded_reports_real_14_step_scoring_separately_from_requested_horizon(self):
        history = pd.DataFrame({'target': np.arange(70, dtype=float) + 1},
                               index=pd.date_range('2026-01-01', periods=70))
        result = fit_guarded(history, horizon=3)
        self.assertEqual(result['evaluation']['requested_serving_horizon'], 3)
        self.assertEqual(result['evaluation']['evaluated_horizon_periods'], 14)
        self.assertEqual(result['selection']['selection_horizon_periods'], 14)
        self.assertEqual(result['evaluation']['scored_steps'], list(range(1, 15)))
        self.assertEqual(result['model_metrics']['mape_denominator_count'], 14)

    def test_api_mode_defaults_historical_but_rejects_unknown_mode(self):
        serializer = TrainForecastRequestSerializer(data={'target_type': TargetType.RETAIL_REVENUE})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['data_mode'], 'historical')
        serializer = TrainForecastRequestSerializer(data={'target_type': TargetType.RETAIL_REVENUE,
                                                          'data_mode': 'trusted_live'})
        self.assertFalse(serializer.is_valid())


@override_settings(TIME_ZONE='Asia/Ho_Chi_Minh')
class OperationalSourceTests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(name='Synthetic fixture', code='op-forecast', workspace_type='RETAIL')
        self.customer = Customer.objects.create(workspace=self.workspace, code='C', name='Synthetic fixture')
        self.config = ForecastModelConfig.objects.create(workspace=self.workspace, name='Guarded',
                         target_type=TargetType.RETAIL_REVENUE, training_config={'strategy': 'guarded_direct_v1'})

    def order(self, day, amount=10):
        return Order.objects.create(workspace=self.workspace, customer=self.customer,
                 order_number=f'SYNTHETIC-{day.isoformat()}', order_date=day,
                 order_timestamp=timezone.make_aware(dt.datetime.combine(day, dt.time(12))),
                 status=OrderStatus.COMPLETED, total_amount=Decimal(amount))

    def history(self, count=70, end=TODAY - dt.timedelta(days=1)):
        for offset in range(count):
            self.order(end - dt.timedelta(days=offset))

    def test_closed_daily_bounds_exclude_today_future_and_never_pad_trailing_unknowns(self):
        self.order(dt.date(2026, 11, 12))
        self.order(dt.date(2026, 11, 14))
        self.order(TODAY)
        self.order(dt.date(2026, 11, 18))
        series = selectors.get_historical_timeseries(self.workspace, TargetType.RETAIL_REVENUE,
                    data_mode='operational', as_of=TODAY)
        self.assertEqual(list(series.index.strftime('%Y-%m-%d')), ['2026-11-12', '2026-11-13', '2026-11-14'])
        self.assertEqual(series.attrs['closed_period_end'], '2026-11-16')
        self.assertEqual(series.attrs['source_period_end'], '2026-11-14')
        self.assertEqual(series.attrs['observed_period_count'], 2)
        self.assertEqual(series.attrs['imputed_period_count'], 1)
        self.assertEqual(series.attrs['commercial_provenance'], 'UNKNOWN')

    def test_closed_weekly_bounds_exclude_both_partial_edge_weeks(self):
        for day in (5, 9, 10, 16, 17, 18):
            self.order(dt.date(2026, 11, day))
        series = selectors.get_historical_timeseries(self.workspace, TargetType.RETAIL_REVENUE,
                    granularity='WEEKLY', data_mode='operational', as_of=TODAY)
        self.assertEqual(list(series.index.strftime('%Y-%m-%d')), ['2026-11-16'])
        self.assertEqual(series.iloc[0]['target'], 20.)
        self.assertEqual(series.attrs['source_period_start'], '2026-11-05')
        self.assertEqual(series.attrs['source_period_end'], '2026-11-16')
        self.assertEqual(series.attrs['source_observation_count'], 4)
        self.assertEqual(series.attrs['observed_daily_coverage'], 4 / 12)

    def test_weekly_monday_is_still_open_and_missing_tail_cannot_be_padded(self):
        for offset in range(20):
            self.order(dt.date(2026, 10, 28) + dt.timedelta(days=offset))
        series = selectors.get_historical_timeseries(self.workspace, TargetType.RETAIL_REVENUE,
                    granularity='WEEKLY', data_mode='operational', as_of=dt.date(2026, 11, 16))
        self.assertEqual(series.attrs['closed_period_end'], '2026-11-09')
        self.assertEqual(list(series.index.strftime('%Y-%m-%d')), ['2026-11-09'])
        series = selectors.get_historical_timeseries(self.workspace, TargetType.RETAIL_REVENUE,
                    granularity='WEEKLY', data_mode='operational', as_of=dt.date(2026, 11, 24))
        self.assertEqual(list(series.index.strftime('%Y-%m-%d')), ['2026-11-09', '2026-11-16'])
        self.assertEqual(series.attrs['source_period_end'], '2026-11-16')

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_preflight_rejects_stale_before_creating_run(self, _):
        self.history(end=dt.date(2026, 9, 1))
        with self.assertRaisesMessage(ValueError, 'OPERATIONAL_DATA_NOT_READY'):
            services.execute_training_job(self.workspace, TargetType.RETAIL_REVENUE, data_mode='operational')
        self.assertEqual(ForecastRun.objects.count(), 0)

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_preflight_distinguishes_sparse_imputed_history_from_observations(self, _):
        self.order(TODAY - dt.timedelta(days=70))
        self.order(TODAY - dt.timedelta(days=1))
        result = services.get_forecast_readiness(self.workspace, TargetType.RETAIL_REVENUE)
        self.assertFalse(result['ready'])
        self.assertIn('INSUFFICIENT_OBSERVED_PERIODS', result['reasons'])
        self.assertIn('LOW_OBSERVED_COVERAGE', result['reasons'])
        self.assertEqual(result['observed_period_count'], 2)

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_current_observed_history_is_eligible_without_claiming_truth_or_accuracy(self, _):
        self.history()
        result = services.get_forecast_readiness(self.workspace, TargetType.RETAIL_REVENUE)
        self.assertTrue(result['ready'])
        self.assertFalse(result['operationally_validated'])
        self.assertEqual(result['commercial_provenance'], 'UNKNOWN')

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_readiness_uses_view_permission_is_read_only_and_workspace_scoped(self, _):
        self.history()
        user = User.objects.create_user(username='readiness-viewer')
        role = Role.objects.create(name='EMPLOYEE')
        perm, _ = Permission.objects.get_or_create(codename='forecasting.view_forecast', defaults={'name': 'View', 'module': 'forecasting'})
        role.permissions.add(perm)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=user, role=role)
        client = APIClient()
        client.force_authenticate(user)
        response = client.get('/api/v1/forecasting/readiness/', {'target_type': TargetType.RETAIL_REVENUE}, HTTP_X_WORKSPACE_ID=str(self.workspace.pk))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['data']['ready'])
        self.assertEqual(ForecastRun.objects.count(), 0)
        role.permissions.clear()
        response = client.get('/api/v1/forecasting/readiness/', {'target_type': TargetType.RETAIL_REVENUE}, HTTP_X_WORKSPACE_ID=str(self.workspace.pk))
        self.assertEqual(response.status_code, 403)

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_serializer_and_chart_assess_the_same_saved_forecast_dates(self, _):
        self.history()
        run = ForecastRun.objects.create(workspace=self.workspace, model_config=self.config,
                 target_type=TargetType.RETAIL_REVENUE, status='COMPLETED', dataset_period_end=TODAY-dt.timedelta(days=2))
        for offset in (-1, 0, 1):
            ForecastResult.objects.create(workspace=self.workspace, forecast_run=run,
                target_type=run.target_type, forecast_date=TODAY+dt.timedelta(days=offset), predicted_value=10)
        chart = services.get_forecast_chart_data(self.workspace)
        self.assertEqual(ForecastRunSerializer(run).data['snapshot_assessment'], chart['snapshot'])

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_weekly_source_freshness_does_not_mistake_future_bin_label_for_future_source(self, _):
        self.config.granularity = 'WEEKLY'
        self.config.save()
        run = ForecastRun.objects.create(workspace=self.workspace, model_config=self.config,
                 target_type=TargetType.RETAIL_REVENUE, status='COMPLETED',
                 dataset_period_end=dt.date(2026, 11, 23),
                 job_parameters={'data_mode': 'historical', 'provenance': {
                     'granularity': 'WEEKLY', 'dataset': {'source_period_end': '2026-11-17'}}})
        ForecastResult.objects.create(workspace=self.workspace, forecast_run=run,
                target_type=run.target_type, forecast_date=dt.date(2026, 11, 30), predicted_value=10)
        chart = services.get_forecast_chart_data(self.workspace)
        self.assertEqual(chart['snapshot']['status'], 'OPEN_PERIOD')
        self.assertEqual(chart['snapshot']['period_end'], '2026-11-17')
        self.assertEqual(ForecastRunSerializer(run).data['snapshot_assessment'], chart['snapshot'])

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_chart_keeps_inactive_saved_run_but_reports_incompatibility(self, _):
        self.history()
        run = ForecastRun.objects.create(workspace=self.workspace, model_config=self.config,
                 target_type=TargetType.RETAIL_REVENUE, status='COMPLETED', dataset_period_end=TODAY-dt.timedelta(days=1))
        self.config.is_active = False
        self.config.save()
        chart = services.get_forecast_chart_data(self.workspace)
        self.assertEqual(chart['run_id'], run.pk)
        self.assertFalse(chart['compatibility']['compatible'])
        self.assertIn('NO_ACTIVE_CONFIGURATION', chart['compatibility']['reasons'])

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_operational_training_saves_readiness_and_excludes_open_future_sources(self, _):
        self.history()
        self.order(TODAY, 99999)
        self.order(TODAY + dt.timedelta(days=1), 99999)
        from apps.forecasting.training import train_forecast_model
        with tempfile.TemporaryDirectory(dir=Path(settings.BASE_DIR) / 'ml_models' / 'forecasting') as artifact_dir:
            with override_settings(FORECASTING_ARTIFACTS_DIR=Path(artifact_dir)):
                run = train_forecast_model(self.workspace, TargetType.RETAIL_REVENUE,
                                          model_config=self.config, data_mode='operational', horizon_days=3)
        self.assertEqual(run.status, 'COMPLETED')
        self.assertEqual(run.dataset_period_end, dt.date(2026, 11, 16))
        self.assertEqual(run.job_parameters['data_mode'], 'operational')
        self.assertTrue(run.job_parameters['readiness']['ready'])
        from apps.forecasting.diagnostics import assess_run_compatibility
        self.assertTrue(assess_run_compatibility(run)['operational_eligible'])
        self.assertEqual(run.job_parameters['provenance']['evaluation']['evaluated_horizon_periods'], 14)
        self.assertEqual(list(run.results.values_list('forecast_date', flat=True)), [TODAY, dt.date(2026, 11, 18), dt.date(2026, 11, 19)])

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_deleting_observed_zero_changes_evidence_even_when_values_and_readiness_stay_valid(self, _):
        self.history()
        interior = TODAY - dt.timedelta(days=30)
        Order.objects.filter(workspace=self.workspace, order_date=interior).update(total_amount=0)
        from apps.forecasting.training import train_forecast_model
        from apps.forecasting.diagnostics import assess_run_compatibility
        with tempfile.TemporaryDirectory(dir=Path(settings.BASE_DIR) / 'ml_models' / 'forecasting') as artifact_dir:
            with override_settings(FORECASTING_ARTIFACTS_DIR=Path(artifact_dir)):
                run = train_forecast_model(self.workspace, TargetType.RETAIL_REVENUE,
                                          model_config=self.config, data_mode='operational', horizon_days=3)
        self.assertTrue(assess_run_compatibility(run)['operational_eligible'])
        frozen_parameters, frozen_metrics = deepcopy(run.job_parameters), deepcopy(run.model_metrics)
        frozen_results = list(run.results.values_list('forecast_date', 'predicted_value'))
        # Disposable TEST fixture only: removing one observed zero becomes an
        # imputed zero; the historical target array is deliberately identical.
        Order.objects.filter(workspace=self.workspace, order_date=interior).delete()
        current = selectors.get_historical_timeseries(self.workspace, TargetType.RETAIL_REVENUE, data_mode='operational')
        value_hash = hashlib.sha256(pd.util.hash_pandas_object(current, index=True).values.tobytes()).hexdigest()
        self.assertEqual(value_hash, frozen_parameters['provenance']['dataset']['fingerprint_sha256'])
        readiness = services.get_forecast_readiness(self.workspace, TargetType.RETAIL_REVENUE)
        self.assertTrue(readiness['ready'])
        self.assertEqual(readiness['observed_period_coverage'], 69 / 70)
        compatibility = assess_run_compatibility(run)
        self.assertFalse(compatibility['compatible'])
        self.assertFalse(compatibility['operational_eligible'])
        self.assertIn('OBSERVATION_EVIDENCE_CHANGED', compatibility['reasons'])
        run.refresh_from_db()
        self.assertEqual(run.job_parameters, frozen_parameters)
        self.assertEqual(run.model_metrics, frozen_metrics)
        self.assertEqual(list(run.results.values_list('forecast_date', 'predicted_value')), frozen_results)

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_legacy_missing_observation_fingerprint_remains_unassessed_without_backfill(self, _):
        self.history()
        from apps.forecasting.training import train_forecast_model
        from apps.forecasting.diagnostics import assess_run_compatibility
        with tempfile.TemporaryDirectory(dir=Path(settings.BASE_DIR) / 'ml_models' / 'forecasting') as artifact_dir:
            with override_settings(FORECASTING_ARTIFACTS_DIR=Path(artifact_dir)):
                run = train_forecast_model(self.workspace, TargetType.RETAIL_REVENUE,
                                          model_config=self.config, data_mode='operational', horizon_days=3)
        run.job_parameters['provenance']['dataset'].pop('observation_evidence_fingerprint_sha256', None)
        run.save(update_fields=['job_parameters'])  # Simulate a pre-change saved run in TEST only.
        frozen_parameters, frozen_metrics = deepcopy(run.job_parameters), deepcopy(run.model_metrics)
        result = assess_run_compatibility(run)
        self.assertIsNone(result['compatible'])
        self.assertFalse(result['operational_eligible'])
        self.assertIn('OBSERVATION_EVIDENCE_FINGERPRINT_UNAVAILABLE', result['unassessed'])
        run.refresh_from_db()
        self.assertEqual(run.job_parameters, frozen_parameters)
        self.assertEqual(run.model_metrics, frozen_metrics)

    def test_weekly_evidence_tracks_source_days_not_just_equal_weekly_totals(self):
        self.config.granularity = 'WEEKLY'
        self.config.save(update_fields=['granularity'])
        for offset in range(21):
            self.order(dt.date(2026, 10, 27) + dt.timedelta(days=offset), amount=0 if offset == 8 else 10)
        from apps.forecasting.training import build_run_provenance

        def capture():
            series = selectors.get_historical_timeseries(self.workspace, TargetType.RETAIL_REVENUE,
                        granularity='WEEKLY', data_mode='operational', as_of=TODAY)
            provenance = build_run_provenance(series, workspace=self.workspace,
                        target_type=TargetType.RETAIL_REVENUE, model_config=self.config,
                        feature_config={}, training_config=self.config.training_config, horizon_days=3, dimensions={})
            return series, provenance['dataset']

        before_series, before = capture()
        Order.objects.filter(workspace=self.workspace, order_date=dt.date(2026, 11, 4)).delete()
        after_series, after = capture()
        self.assertEqual(before['fingerprint_sha256'], after['fingerprint_sha256'])
        self.assertEqual(before_series.attrs['observed_period_dates'], after_series.attrs['observed_period_dates'])
        self.assertNotEqual(before.get('observation_evidence_fingerprint_sha256'),
                            after.get('observation_evidence_fingerprint_sha256'))

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_historical_training_explicitly_records_ineligibility_without_rewriting_source(self, _):
        self.history()
        self.order(TODAY)
        self.order(TODAY + dt.timedelta(days=1))
        from apps.forecasting.training import train_forecast_model
        with tempfile.TemporaryDirectory(dir=Path(settings.BASE_DIR) / 'ml_models' / 'forecasting') as artifact_dir:
            with override_settings(FORECASTING_ARTIFACTS_DIR=Path(artifact_dir)):
                run = train_forecast_model(self.workspace, TargetType.RETAIL_REVENUE,
                                          model_config=self.config, data_mode='historical', horizon_days=3)
        self.assertEqual(run.dataset_period_end, dt.date(2026, 11, 18))
        self.assertFalse(run.job_parameters['readiness']['ready'])
        self.assertIn('HISTORICAL_MODE', run.job_parameters['readiness']['reasons'])
        self.assertEqual(run.job_parameters['provenance']['dataset']['future_day_observation_count'], 1)
        self.assertEqual(Order.objects.count(), 72)

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_queued_operational_run_cannot_train_after_config_revision(self, _):
        self.history()
        with override_settings(FORECAST_ASYNC_ENABLED=True):
            run = services.execute_training_job(self.workspace, TargetType.RETAIL_REVENUE,
                                                data_mode='operational', is_async=True)
        self.config.feature_config = {'lags': [1, 14]}
        self.config.save()
        from apps.forecasting.training import train_forecast_model
        with self.assertRaisesMessage(ValueError, 'CONFIGURATION_CHANGED'):
            train_forecast_model(self.workspace, TargetType.RETAIL_REVENUE, run=run)
        run.refresh_from_db()
        self.assertEqual(run.status, 'FAILED')
        self.assertEqual(run.results.count(), 0)

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_compatibility_separates_late_source_edits_from_new_observations(self, _):
        self.history()
        from apps.forecasting.training import build_run_provenance
        series = selectors.get_historical_timeseries(self.workspace, TargetType.RETAIL_REVENUE)
        provenance = build_run_provenance(series, workspace=self.workspace,
                    target_type=TargetType.RETAIL_REVENUE, model_config=self.config,
                    feature_config={}, training_config=self.config.training_config, horizon_days=14, dimensions={})
        run = ForecastRun.objects.create(workspace=self.workspace, model_config=self.config,
                    target_type=TargetType.RETAIL_REVENUE, status='COMPLETED',
                    dataset_period_start=series.index[0].date(), dataset_period_end=series.index[-1].date(),
                    job_parameters={'provenance': provenance})
        self.order(TODAY)
        result = services.get_forecast_chart_data(self.workspace)['compatibility']
        self.assertTrue(result['compatible'])
        self.assertTrue(result['new_observations_available'])
        Order.objects.filter(workspace=self.workspace, order_date=run.dataset_period_end).update(total_amount=99)
        result = services.get_forecast_chart_data(self.workspace)['compatibility']
        self.assertFalse(result['compatible'])
        self.assertIn('HISTORY_CHANGED', result['reasons'])

    @patch('django.utils.timezone.localdate', return_value=TODAY)
    def test_new_closed_observations_are_detected_after_operational_training_as_of(self, clock):
        self.history()
        from apps.forecasting.training import build_run_provenance
        from apps.forecasting.diagnostics import assess_run_compatibility
        series = selectors.get_historical_timeseries(self.workspace, TargetType.RETAIL_REVENUE, data_mode='operational')
        provenance = build_run_provenance(series, workspace=self.workspace,
                    target_type=TargetType.RETAIL_REVENUE, model_config=self.config,
                    feature_config={}, training_config=self.config.training_config, horizon_days=14, dimensions={})
        run = ForecastRun.objects.create(workspace=self.workspace, model_config=self.config,
                    target_type=TargetType.RETAIL_REVENUE, status='COMPLETED',
                    dataset_period_start=series.index[0].date(), dataset_period_end=series.index[-1].date(),
                    job_parameters={'data_mode': 'operational', 'readiness': services.get_forecast_readiness(self.workspace, TargetType.RETAIL_REVENUE),
                                    'provenance': provenance})
        self.order(TODAY)
        clock.return_value = TODAY + dt.timedelta(days=1)
        result = assess_run_compatibility(run)
        self.assertTrue(result['compatible'])
        self.assertTrue(result['new_observations_available'])

    @override_settings(HOME_DELIVERY_FULFILLMENT_POLICY='legacy')
    def test_public_checkout_uses_local_business_day_at_utc_rollover(self):
        from django.test import Client
        category = Category.objects.create(workspace=self.workspace, code='CAT-P', name='Synthetic')
        product = Product.objects.create(workspace=self.workspace, category=category, sku='SKU-P', name='Synthetic', unit_price=10)
        client = Client()
        client.post(f'/gio-hang/them/{product.pk}/', {'quantity': '1'})
        stamp = dt.datetime(2026, 11, 16, 18, tzinfo=dt.timezone.utc)
        with patch('apps.public_web.views.timezone.now', return_value=stamp):
            response = client.post('/thanh-toan/dat-hang/', {'name': 'Synthetic', 'phone': '0900000000',
                'email': 'synthetic@example.invalid', 'delivery_method': 'HOME_DELIVERY', 'address': 'Synthetic'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.get().order_date, TODAY)

    def test_retail_default_date_uses_business_timezone_and_preserves_explicit_date(self):
        from apps.retail.services import create_order
        category = Category.objects.create(workspace=self.workspace, code='CAT', name='Synthetic')
        product = Product.objects.create(workspace=self.workspace, category=category, sku='SKU', name='Synthetic', unit_price=10)
        stamp = dt.datetime(2026, 11, 16, 18, tzinfo=dt.timezone.utc)
        payload = {'customer_id': self.customer.pk, 'items': [{'product_id': product.pk, 'quantity': 1}], 'order_timestamp': stamp}
        order = create_order(self.workspace, None, payload)
        self.assertEqual(order.order_date, TODAY)
        payload['order_date'] = dt.date(2020, 1, 2)
        order = create_order(self.workspace, None, payload)
        self.assertEqual(order.order_date, dt.date(2020, 1, 2))
