import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from apps.forecasting.artifacts import load_run_artifact, save_run_artifact


FORMAT = "alphatech_guarded_forecast_v1"


def make_run(root, *, run_id=17, workspace_id="ws-a", lease_token="lease-1"):
    return SimpleNamespace(
        id=run_id,
        workspace_id=workspace_id,
        target_type="RETAIL_REVENUE",
        lease_token=lease_token,
        job_parameters={"provenance": {"source_hash": "source"}},
        artifact_path="",
        save=lambda: (_ for _ in ()).throw(AssertionError("save() must not be called")),
    )


def roots(temp):
    base = Path(temp)
    artifacts = base / "ml_models" / "forecasting"
    return base, artifacts


def payload():
    return {"format": FORMAT, "effective_model": "MA7", "booster": None, "columns": []}


class GuardedForecastArtifactTests(unittest.TestCase):
    def test_save_binds_payload_and_writes_verified_snapshot_without_db_save(self):
        with tempfile.TemporaryDirectory() as temp:
            base, artifacts = roots(temp)
            run = make_run(temp)
            original = payload()
            before = json.loads(json.dumps(original))

            save_run_artifact(run, original, base_dir=base, artifacts_dir=artifacts)

            self.assertEqual(original, before)
            self.assertEqual(run.artifact_path, f"ml_models/forecasting/{Path(run.artifact_path).name}")
            disk = (base / run.artifact_path).read_bytes()
            snapshot = run.job_parameters["artifact_snapshot"]
            digest = hashlib.sha256(disk).hexdigest()
            self.assertEqual(snapshot, {"body": disk.decode("utf-8"), "bytes": len(disk), "format": FORMAT, "sha256": digest})
            self.assertEqual(run.job_parameters["provenance"]["artifact_sha256"], digest)
            self.assertEqual(json.loads(disk)["scope"], {"workspace_id": "ws-a", "run_id": 17, "target_type": "RETAIL_REVENUE"})
            self.assertEqual(load_run_artifact(run, base_dir=base, artifacts_dir=artifacts)["effective_model"], "MA7")

    def test_rejects_payload_larger_than_one_mib(self):
        with tempfile.TemporaryDirectory() as temp:
            base, artifacts = roots(temp)
            with self.assertRaises(ValueError):
                save_run_artifact(make_run(temp), {**payload(), "blob": "x" * 1_048_576}, base_dir=base, artifacts_dir=artifacts)

    def test_oversized_disk_artifact_is_rejected_after_only_a_bounded_read(self):
        with tempfile.TemporaryDirectory() as temp:
            base, artifacts = roots(temp)
            run = make_run(temp)
            save_run_artifact(run, payload(), base_dir=base, artifacts_dir=artifacts)
            original_open = Path.open
            requested_sizes = []
            target = (base / run.artifact_path).resolve()

            class OversizedReader:
                def __enter__(self):
                    return self

                def __exit__(self, *exc):
                    return False

                def read(self, size=-1):
                    requested_sizes.append(size)
                    if size < 0 or size > 1_048_577:
                        raise AssertionError("artifact stream read was not bounded")
                    return b"x" * 1_048_577

            def bounded_open(path, *args, **kwargs):
                if path.resolve() == target:
                    return OversizedReader()
                return original_open(path, *args, **kwargs)

            with patch.object(Path, "open", bounded_open):
                with self.assertRaises(ValueError):
                    load_run_artifact(run, base_dir=base, artifacts_dir=artifacts)
            self.assertEqual(requested_sizes, [1_048_577])

    def test_run_scope_requires_positive_integer_id(self):
        with tempfile.TemporaryDirectory() as temp:
            base, artifacts = roots(temp)
            for invalid_id in (True, 17.5, 0, -3, "17"):
                run = make_run(temp, run_id=invalid_id)
                with self.subTest(run_id=invalid_id), self.assertRaises(ValueError):
                    save_run_artifact(run, payload(), base_dir=base, artifacts_dir=artifacts)

    def test_rejects_oversized_snapshot_body_before_encoding(self):
        with tempfile.TemporaryDirectory() as temp:
            base, artifacts = roots(temp)
            run = make_run(temp)
            save_run_artifact(run, payload(), base_dir=base, artifacts_dir=artifacts)
            (base / run.artifact_path).unlink()
            snapshot = run.job_parameters["artifact_snapshot"]

            class OversizedText(str):
                def encode(self, *args, **kwargs):
                    raise AssertionError("oversized snapshot was encoded before its length check")

            snapshot["body"] = OversizedText("x" * 1_048_577)
            with self.assertRaises(ValueError):
                load_run_artifact(run, base_dir=base, artifacts_dir=artifacts)

    def test_rejects_nonfinite_and_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            base, artifacts = roots(temp)
            with self.assertRaises(ValueError):
                save_run_artifact(make_run(temp), {**payload(), "bad": float("nan")}, base_dir=base, artifacts_dir=artifacts)

            run = make_run(temp)
            save_run_artifact(run, payload(), base_dir=base, artifacts_dir=artifacts)
            path = base / run.artifact_path
            raw = ('{"format":"%s","format":"%s","scope":{"workspace_id":"ws-a","run_id":17,"target_type":"RETAIL_REVENUE"}}' % (FORMAT, FORMAT)).encode()
            path.write_bytes(raw)
            run.artifact_path = path.relative_to(base).as_posix()
            run.job_parameters["provenance"]["artifact_sha256"] = hashlib.sha256(raw).hexdigest()
            with self.assertRaises(ValueError):
                load_run_artifact(run, base_dir=base, artifacts_dir=artifacts)

    def test_disk_tamper_is_error_even_when_snapshot_is_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            base, artifacts = roots(temp)
            run = make_run(temp)
            save_run_artifact(run, payload(), base_dir=base, artifacts_dir=artifacts)
            (base / run.artifact_path).write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_run_artifact(run, base_dir=base, artifacts_dir=artifacts)

    def test_missing_disk_uses_verified_inline_snapshot_without_recreating_file(self):
        with tempfile.TemporaryDirectory() as temp:
            base, artifacts = roots(temp)
            run = make_run(temp)
            save_run_artifact(run, payload(), base_dir=base, artifacts_dir=artifacts)
            (base / run.artifact_path).unlink()
            loaded = load_run_artifact(run, base_dir=base, artifacts_dir=artifacts)
            self.assertEqual(loaded["effective_model"], "MA7")
            self.assertFalse((base / run.artifact_path).exists())

    def test_missing_disk_without_snapshot_is_error(self):
        with tempfile.TemporaryDirectory() as temp:
            base, artifacts = roots(temp)
            run = make_run(temp)
            save_run_artifact(run, payload(), base_dir=base, artifacts_dir=artifacts)
            (base / run.artifact_path).unlink()
            run.job_parameters.pop("artifact_snapshot")
            with self.assertRaises(ValueError):
                load_run_artifact(run, base_dir=base, artifacts_dir=artifacts)

    def test_rejects_foreign_scope_even_when_snapshot_hash_is_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            base, artifacts = roots(temp)
            run = make_run(temp)
            save_run_artifact(run, payload(), base_dir=base, artifacts_dir=artifacts)
            run.workspace_id = "ws-other"
            with self.assertRaises(PermissionError):
                load_run_artifact(run, base_dir=base, artifacts_dir=artifacts)

    def test_rejects_traversal_path_before_inline_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            base, artifacts = roots(temp)
            run = make_run(temp)
            save_run_artifact(run, payload(), base_dir=base, artifacts_dir=artifacts)
            run.artifact_path = "ml_models/forecasting/../../outside.json"
            with self.assertRaises((PermissionError, ValueError)):
                load_run_artifact(run, base_dir=base, artifacts_dir=artifacts)

    def test_rejects_symlink_escape_before_inline_recovery(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            base, artifacts = roots(temp)
            run = make_run(temp)
            save_run_artifact(run, payload(), base_dir=base, artifacts_dir=artifacts)
            link = artifacts / "run_17_escape.json"
            try:
                link.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are unavailable")
            run.artifact_path = "ml_models/forecasting/run_17_escape.json"
            with self.assertRaises((PermissionError, ValueError)):
                load_run_artifact(run, base_dir=base, artifacts_dir=artifacts)

    def test_inline_snapshot_must_match_bound_run_and_expected_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            base, artifacts = roots(temp)
            run = make_run(temp)
            save_run_artifact(run, payload(), base_dir=base, artifacts_dir=artifacts)
            (base / run.artifact_path).unlink()
            run.job_parameters["artifact_snapshot"]["body"] = "{}"
            with self.assertRaises(ValueError):
                load_run_artifact(run, base_dir=base, artifacts_dir=artifacts)

    def test_rejects_unknown_format_and_invalid_utf8_on_disk(self):
        with tempfile.TemporaryDirectory() as temp:
            base, artifacts = roots(temp)
            run = make_run(temp)
            save_run_artifact(run, payload(), base_dir=base, artifacts_dir=artifacts)
            path = base / run.artifact_path
            raw = b"\xff"
            path.write_bytes(raw)
            run.job_parameters["provenance"]["artifact_sha256"] = hashlib.sha256(raw).hexdigest()
            run.job_parameters.pop("artifact_snapshot")
            with self.assertRaises(ValueError):
                load_run_artifact(run, base_dir=base, artifacts_dir=artifacts)

            with self.assertRaises(ValueError):
                save_run_artifact(make_run(temp, run_id=18), {**payload(), "format": "wrong"}, base_dir=base, artifacts_dir=artifacts)


if __name__ == "__main__":
    unittest.main()
