import tempfile
import json
import hashlib
from pathlib import Path
from django.test import SimpleTestCase
import pandas as pd
from scripts.forecast_reproducible_experiment import synthetic_dataset, validate_dataset, run


class ForecastExperimentBundleTests(SimpleTestCase):
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
            manifest = json.loads((first / "manifest.json").read_text())
            for name, expected in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256((first / name).read_bytes()).hexdigest(), expected)
            predictions = pd.read_csv(first / "test_predictions.csv")
            self.assertEqual(int(((predictions.actual >= predictions.lower) & (predictions.actual <= predictions.upper)).sum()), result["interval"]["covered"])
            self.assertFalse(result["interval"]["certified_calibration"])
            with self.assertRaises(FileExistsError):
                run(first)
