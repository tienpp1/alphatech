import importlib
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase


class OnlineAiDemoAlgorithmTests(SimpleTestCase):
    def setUp(self):
        try:
            self.lab = importlib.import_module('apps.forecasting.demo_lab')
        except ModuleNotFoundError as exc:
            if exc.name != 'apps.forecasting.demo_lab':
                raise
            self.fail('The fixed-case online demo algorithm service does not exist yet.')

    def test_forecast_matches_archived_pre_holdout_replay(self):
        result = self.lab.run_demo_case('forecast')
        data = result['data']
        self.assertEqual(result['scope'], 'SYNTHETIC_DEMO')
        self.assertEqual((data['model'], data['calendar_mode']), ('XGBOOST_DIRECT', 'full'))
        self.assertEqual(data['training_cutoff'], '2025-08-06')
        self.assertEqual((data['holdout_start'], data['holdout_end']), ('2025-08-07', '2025-12-30'))
        self.assertEqual((data['history_rows'], data['training_rows']), (730, 584))
        self.assertEqual((data['holdout_rows'], data['scored_rows'], data['omitted_rows']), (146, 140, 6))
        self.assertEqual((data['blocks'], data['horizon']), (10, 14))
        reference = {
            'xgboost': (896681.5191052415, 1152831.6882594465),
            'ma7': (4919190.032356063, 5710107.68009616),
            'seasonal_naive_7': (2181772.2214285713, 2818615.6554172514),
        }
        for metric, (mae, rmse) in reference.items():
            with self.subTest(metric=metric):
                self.assertAlmostEqual(data['metrics'][metric]['mae'], mae, delta=.01)
                self.assertAlmostEqual(data['metrics'][metric]['rmse'], rmse, delta=.01)
        first = data['sample_rows'][0]
        self.assertEqual((first['origin'], first['date'], first['step']), ('2025-08-06', '2025-08-07', 1))
        self.assertEqual(first['actual'], 19751401.)
        self.assertAlmostEqual(first['prediction'], 20134700.070852257, delta=.01)
        self.assertNotIn('booster', json.dumps(result))

    def test_forecast_scores_current_inference_using_only_rows_through_each_origin(self):
        from apps.forecasting import guarded

        with patch.object(guarded, 'predict_artifact', return_value=[0.] * 14) as predict:
            data = self.lab.run_demo_case('forecast')['data']
        self.assertEqual([len(call.args[1]) for call in predict.call_args_list], list(range(584, 724, 14)))
        self.assertEqual([call.kwargs['horizon'] for call in predict.call_args_list], [14] * 10)
        self.assertEqual(data['sample_rows'][0]['prediction'], 0.)
        self.assertGreater(data['metrics']['xgboost']['mae'], 20_000_000.)
        self.assertAlmostEqual(data['metrics']['ma7']['mae'], 4919190.032356063, delta=.01)

    def test_retrieval_ranks_two_snippets_with_hash_cosine_and_lexical_overlap(self):
        data = self.lab.run_demo_case('retrieval')['data']
        best, other = data['candidates']
        self.assertEqual(data['source'], best['source'])
        self.assertEqual(data['answer'], best['excerpt'])
        self.assertIn('xác nhận', data['answer'].lower())
        self.assertEqual(best['lexical_score'], 1.)
        self.assertGreater(best['dense_similarity'], other['dense_similarity'])
        self.assertGreater(best['similarity'], other['similarity'])

    def test_pending_mapping_does_not_transform_even_high_confidence_suggestions(self):
        data = self.lab.run_demo_case('mapping_pending')['data']
        self.assertEqual(data['confirmation_status'], 'PENDING')
        self.assertEqual(data['after'], {})
        self.assertEqual(data['errors'], [])
        self.assertTrue(any(row['confidence'] >= .95 for row in data['suggestions']))

    def test_confirmed_mapping_uses_canonical_fields_and_reports_unmapped_enum(self):
        data = self.lab.run_demo_case('mapping_confirmed')['data']
        self.assertEqual(data['before'], self.lab.run_demo_case('mapping_pending')['data']['before'])
        self.assertEqual(data['confirmation_status'], 'ACCEPTED')
        self.assertEqual(data['after'], {'customer_id': 'DEMO-KH-01', 'name': 'Khách mô phỏng A'})
        self.assertEqual([(error['source_field'], error['target_field']) for error in data['errors']],
                         [('phan_khuc', 'segment')])

    def test_recommendation_ranks_available_candidates_and_previews_tool_schema_only(self):
        data = self.lab.run_demo_case('recommendation')['data']
        best, other, unavailable = data['candidates']
        self.assertEqual(data['selected_candidate'], best['name'])
        self.assertEqual([best['score'], other['score'], unavailable['score']], [85., 75., 0.])
        self.assertFalse(unavailable['is_available'])
        self.assertEqual(unavailable['subscores']['availability_score'], 0.)
        self.assertEqual(best['weights'], {'distance': .5, 'workload': .5, 'skill': 0.})
        self.assertEqual(data['tool'], {
            'name': 'dispatch_technician', 'classification': 'MUTATION', 'risk_level': 'HIGH',
            'required_permission': 'service_ops.change_servicerequest',
            'schema_valid': True, 'check_domain': False,
        })

    def test_demo_does_not_fit_query_or_contact_a_provider(self):
        # SimpleTestCase disallows database access; trap training and the provider transport too.
        from apps.forecasting import adaptive, guarded

        forbidden = AssertionError('The online demo cannot train or contact a provider.')
        with (patch.object(adaptive, 'fit_direct', side_effect=forbidden),
              patch.object(guarded, 'fit_guarded', side_effect=forbidden),
              patch('socket.socket.connect', side_effect=forbidden),
              patch('apps.knowledge.embedding.open_provider_request', side_effect=forbidden)):
            for case in self.lab.DEMO_CASES:
                with self.subTest(case=case):
                    result = self.lab.run_demo_case(case)
                    self.assertEqual(result['case'], case)
                    self.assertEqual(result['scope'], 'SYNTHETIC_DEMO')
                    self.assertTrue(result['execution_mode'])
                    self.assertTrue(result['warnings'])
                    json.dumps(result, allow_nan=False)

    def test_rejects_cases_outside_fixed_allowlist(self):
        for case in ('', ' forecast', 'forecast/../../../', 'FORECAST', ['forecast'], None):
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.lab.run_demo_case(case)

    def test_forecast_rejects_corrupt_model_before_loading_it(self):
        from apps.forecasting import guarded

        with TemporaryDirectory() as directory:
            assets = Path(directory) / 'assets'
            shutil.copytree(self.lab.DEMO_ASSET_DIR, assets)
            path = assets / 'evaluation_model.json'
            path.write_bytes(path.read_bytes() + b' ')
            with (patch.object(self.lab, 'DEMO_ASSET_DIR', assets),
                  patch.object(guarded, 'predict_artifact', side_effect=AssertionError('Unsafe asset reached prediction')),
                  self.assertRaises(ValueError)):
                self.lab.run_demo_case('forecast')

    def test_forecast_rejects_serving_cutoff_metadata(self):
        from apps.forecasting import guarded

        with TemporaryDirectory() as directory:
            assets = Path(directory) / 'assets'
            shutil.copytree(self.lab.DEMO_ASSET_DIR, assets)
            manifest_path = assets / 'manifest.json'
            manifest = json.loads(manifest_path.read_bytes())
            manifest['training_cutoff'] = '2025-12-30'
            manifest['training_rows'] = 730
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            with (patch.object(self.lab, 'DEMO_ASSET_DIR', assets),
                  patch.object(guarded, 'predict_artifact', side_effect=AssertionError('Unsafe cutoff reached prediction')),
                  self.assertRaises(ValueError)):
                self.lab.run_demo_case('forecast')

    def test_forecast_rejects_changed_manifest_before_parsing(self):
        original_asset_bytes = self.lab._asset_bytes
        original = original_asset_bytes('manifest.json', 8192)
        changed = json.loads(original)
        del changed['build_runtime'], changed['engine_source_sha256']
        changed.update(archived_holdout_parity_rows=0, validation_blocks=False)
        manifests = {
            'erased build evidence': json.dumps(changed).encode('utf-8'),
            'deep JSON within the byte cap': original.rstrip()[:-1] + b',"extra":' + (
                b'[' * 2000 + b'0' + b']' * 2000 + b'}'),
        }
        for label, raw in manifests.items():
            with (self.subTest(label=label),
                  patch.object(self.lab, '_asset_bytes', side_effect=lambda name, limit: (
                      raw if name == 'manifest.json' else original_asset_bytes(name, limit)))):
                try:
                    with self.assertRaisesRegex(ValueError, 'manifest SHA-256 mismatch'):
                        self.lab.run_demo_case('forecast')
                except RecursionError:
                    self.fail('Unverified manifest reached recursive JSON parsing.')
