"""
Academic Test Manifest Audit Test Suite (Gate 86 Verification).

Validates the completeness, accuracy, and disaggregation of the test manifest
documented in docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md (Section 4).

Invariants enforced:
1. Every test_*.py file in tests/ must be explicitly accounted for in the manifest.
2. Tests are strictly disaggregated across the 12 core business modules + cross-cutting.
3. Historical development failures and architectural resolutions are documented.
4. Conditional skips (@skipUnlessDBFeature, skipTest) are enumerated and justified.
5. Unrun external scopes match exactly the 8 unconfirmed production gates (Gates 90-97).
"""

import os
from pathlib import Path
from django.test import SimpleTestCase
from django.conf import settings
from django.test.runner import DiscoverRunner


class AcademicTestManifestAuditTestCase(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_dir = Path(settings.BASE_DIR)
        cls.manifest_path = cls.base_dir / "docs" / "HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md"
        cls.checklist_path = cls.base_dir / "docs" / "CHECKLIST_97_PROGRESS.md"
        
        with open(cls.manifest_path, "r", encoding="utf-8") as f:
            cls.manifest_content = f.read()

        with open(cls.checklist_path, "r", encoding="utf-8") as f:
            cls.checklist_content = f.read()

    def test_all_test_files_accounted_in_manifest(self):
        """Every test_*.py file in tests/ must be explicitly named in the manifest."""
        tests_dir = self.base_dir / "tests"
        test_files = [f.name for f in tests_dir.iterdir() if f.is_file() and f.name.startswith("test_") and f.name.endswith(".py")]
        
        missing_files = []
        for tf in test_files:
            if tf not in self.manifest_content:
                missing_files.append(tf)

        self.assertEqual(
            missing_files,
            [],
            f"The following test files are missing from docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md: {missing_files}"
        )

    def test_manifest_disaggregates_12_modules(self):
        """Manifest must partition tests into modular domains rather than a single lumped sum."""
        expected_modules = [
            "1. AUTH & SECURITY",
            "2. WORKSPACES & ISOLATION",
            "3. RETAIL COMMERCE",
            "4. SERVICE OPERATIONS",
            "5. GIS & SPATIAL",
            "6. DATA INTEGRATION & MAPPING",
            "7. ENTERPRISE RAG & INTENT",
            "8. TIME-SERIES FORECASTING",
            "9. ACTIONS & APPROVALS",
            "10. NOTIFICATIONS & OUTBOX",
            "11. BULLETIN BOARD",
            "12. TEAM CHAT",
            "CROSS-CUTTING / INTEGRITY",
        ]
        for mod in expected_modules:
            self.assertIn(mod, self.manifest_content, f"Modular grouping '{mod}' missing from Section 4.3.1")

    def test_historical_failures_and_architectural_resolutions_documented(self):
        """Manifest must document the 8 historical failures and their architectural resolutions."""
        expected_failures = [
            "Audit Log bị Rollback khi Giao dịch Thất bại",
            "Lỗ hổng Tự Duyệt Hành động (Self-Approval)",
            "Tranh chấp Tồn kho khi Đặt hàng Đồng thời (Race Condition)",
            "Lỗi `NoneType` khi Tính Deadline SLA Phiếu Dịch vụ",
            "Xung đột Chiều Không gian Embedding trong RAG (Dimension Mismatch)",
            "Lỗi Quá Tải Yêu cầu Geocoding (HTTP 429 Too Many Requests)",
            "Độ Lệch Doanh thu Bán lẻ Kém Baseline (-38,7% MAE)",
            "Cam kết Thương mại Soạn sẵn Chưa Xác minh và Lộ SOP Nội bộ",
        ]
        for fail in expected_failures:
            self.assertIn(fail, self.manifest_content, f"Historical failure '{fail}' missing from Section 4.3.2")

    def test_conditional_skips_are_strictly_tracked(self):
        """Manifest must accurately catalog conditional skips and their prerequisites."""
        self.assertIn("test_brevo_email_backend.py", self.manifest_content)
        self.assertIn("has_select_for_update", self.manifest_content)
        self.assertIn("test_audit_trail_evidence.py", self.manifest_content)
        self.assertIn("Database-level trigger enforcement requires PostgreSQL", self.manifest_content)
        self.assertIn("0 bài kiểm thử bị bỏ qua (0 skipped tests)", self.manifest_content)

    def test_unrun_scopes_match_unconfirmed_production_gates(self):
        """Manifest must delineate the 8 production gates (90-97) without masking or lumping."""
        expected_gates = [
            "Cổng 90",
            "Cổng 91",
            "Cổng 92",
            "Cổng 93",
            "Cổng 94",
            "Cổng 95",
            "Cổng 96",
            "Cổng 97",
        ]
        for gate in expected_gates:
            self.assertIn(gate, self.manifest_content, f"Production gate '{gate}' missing from Section 4.3.4")

        # Verify specific scope justifications exist
        self.assertIn("Khớp Phiên bản Git Commit Triển khai", self.manifest_content)
        self.assertIn("Bằng chứng Giao nhận Email Thật", self.manifest_content)
        self.assertIn("Vận hành Worker Nền tảng Đám mây", self.manifest_content)
        self.assertIn("Đường ống CI/CD GitHub Actions", self.manifest_content)
        self.assertIn("Thu thập Lỗi Vận hành Thời gian thực qua Sentry", self.manifest_content)
        self.assertIn("Cấu hình Chứng chỉ SSL/HTTPS", self.manifest_content)
        self.assertIn("Quy trình Khôi phục Thảm họa Cơ sở Dữ liệu (`pg_dump`", self.manifest_content)
        self.assertIn("Quản lý & Luân chuyển Khóa Bí mật qua Cloud HSM/KMS", self.manifest_content)

    def test_total_django_test_discovery_scale(self):
        """Discovered test count must be at least 1,050 tests across the repository."""
        runner = DiscoverRunner()
        suite = runner.build_suite(["tests"])
        total_discovered = suite.countTestCases()
        self.assertGreaterEqual(
            total_discovered,
            1050,
            f"Expected at least 1,050 discovered tests, got {total_discovered}"
        )
