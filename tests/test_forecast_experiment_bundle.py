import tempfile
import json
import hashlib
from pathlib import Path
from django.test import SimpleTestCase
import pandas as pd
from scripts.forecast_reproducible_experiment import synthetic_dataset, validate_dataset, run


class ForecastExperimentBundleTests(SimpleTestCase):
    def test_recursive_predictions_do_not_depend_on_future_actuals(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, altered = Path(tmp) / 'first', Path(tmp) / 'altered'
            run(first)
            frame = pd.read_csv(first / 'dataset.csv', index_col='date', parse_dates=True)
            recursive = pd.read_csv(first / 'recursive_predictions.csv', index_col='date')
            frame.loc[pd.Timestamp(recursive.index[0]):, 'target'] += 10_000_000
            snapshot = Path(tmp) / 'changed.csv'
            frame.to_csv(snapshot, index_label='date')
            run(altered, snapshot)
            after = pd.read_csv(altered / 'recursive_predictions.csv', index_col='date')
            pd.testing.assert_frame_equal(recursive[['prediction', 'lag7', 'ma7']], after[['prediction', 'lag7', 'ma7']])
            self.assertFalse(recursive.actual.equals(after.actual))

    def test_ui_does_not_claim_calibrated_coverage(self):
        template = (Path(__file__).resolve().parents[1] / "templates/forecasting/index.html").read_text(encoding="utf-8")
        self.assertNotIn("Dải dự báo xấp xỉ 95%", template)
        self.assertIn("chưa được hiệu chỉnh để bảo đảm độ bao phủ 95%", template)
        self.assertIn("Cận trên — dải tham khảo, chưa hiệu chỉnh", template)

    def test_missing_or_invalid_data_rejected(self):
        frame = synthetic_dataset()
        with self.assertRaises(ValueError):
            validate_dataset(frame.drop(frame.index[10]))
        frame.iloc[0, 0] = float("nan")
        with self.assertRaises(ValueError):
            validate_dataset(frame)

    def test_snapshot_replay_and_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / "first", Path(tmp) / "second"
            result = run(first)
            replay = run(second, first / "dataset.csv")
            self.assertEqual(result, replay)
            self.assertEqual((first / "test_predictions.csv").read_bytes(), (second / "test_predictions.csv").read_bytes())
            self.assertEqual((first / "recursive_predictions.csv").read_bytes(), (second / "recursive_predictions.csv").read_bytes())
            manifest = json.loads((first / "manifest.json").read_text())
            for name, expected in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256((first / name).read_bytes()).hexdigest(), expected)
            predictions = pd.read_csv(first / "test_predictions.csv")
            self.assertEqual(int(((predictions.actual >= predictions.lower) & (predictions.actual <= predictions.upper)).sum()), result["interval"]["covered"])
            self.assertFalse(result["interval"]["certified_calibration"])
            recursive = pd.read_csv(first / 'recursive_predictions.csv')
            self.assertEqual(len(recursive), 14)
            self.assertEqual(result['recursive_14_day']['horizon'], 14)
            # At step 8 lag7 must reuse its first prediction, NOT first actual.
            self.assertEqual(recursive.iloc[7].lag7, recursive.iloc[0].lag7)
            self.assertNotEqual(recursive.iloc[7].lag7, recursive.iloc[0].actual)
            self.assertAlmostEqual(recursive.iloc[7].ma7, recursive.iloc[:7].ma7.mean())
            from apps.forecasting.evaluation import compute_metrics
            self.assertEqual(compute_metrics(recursive.actual.to_numpy(), recursive.prediction.to_numpy()),
                             result['recursive_14_day']['model'])
            with self.assertRaises(FileExistsError):
                run(first)
