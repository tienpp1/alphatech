"""Tests verifying the academic deployment and operations dossiers for Gates 3, 6, 47, and 90-97."""
from pathlib import Path
from unittest import TestCase
from django.conf import settings


class ProductionDeploymentDossierTests(TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.docs_dir = self.root / "docs"

    def test_all_11_batch_50_dossiers_exist(self):
        """Verify the 3 comprehensive dossiers created in Batch 50 exist and are non-empty."""
        expected_files = [
            "HO_SO_LICH_TRINH_HANH_CHINH_VA_LO_TRINH_PHAT_TRIEN.md",
            "HO_SO_RA_SOAT_TAI_LIEU_SOP_VA_TRONG_TAM_NGHIEP_VU.md",
            "HO_SO_VAN_HANH_HA_TANG_PRODUCTION_VA_DEPLOYMENT_RUNBOOK.md",
        ]
        for filename in expected_files:
            file_path = self.docs_dir / filename
            self.assertTrue(file_path.exists(), f"Dossier {filename} must exist")
            self.assertGreater(file_path.stat().st_size, 500, f"Dossier {filename} must have substantial content")

    def test_administrative_and_roadmap_dossier_content(self):
        """Verify Gate 3 (Roadmap) and Gate 6 (Faculty Milestones) in the administrative dossier."""
        doc_path = self.docs_dir / "HO_SO_LICH_TRINH_HANH_CHINH_VA_LO_TRINH_PHAT_TRIEN.md"
        content = doc_path.read_text(encoding="utf-8")
        
        # Check Gate 3 coverage
        self.assertTrue("Gate 3" in content or "Cổng 3" in content or "Mục 3" in content)
        self.assertTrue("hướng phát triển tương lai" in content.lower())
        self.assertTrue("lộ trình mở rộng" in content.lower())
        
        # Check Gate 6 coverage
        self.assertTrue("Gate 6" in content or "Cổng 6" in content or "Mục 6" in content)
        self.assertTrue("mốc hành chính" in content.lower())
        self.assertTrue("lịch trình" in content.lower())
        self.assertTrue("bảo vệ" in content.lower())

    def test_sop_scope_dossier_content(self):
        """Verify Gate 47 (SOP out-of-scope reduction) in the SOP dossier."""
        doc_path = self.docs_dir / "HO_SO_RA_SOAT_TAI_LIEU_SOP_VA_TRONG_TAM_NGHIEP_VU.md"
        content = doc_path.read_text(encoding="utf-8")
        
        self.assertTrue("Gate 47" in content or "Cổng 47" in content or "Mục 47" in content)
        self.assertIn("PRIMARY_SOPS", content)
        self.assertIn("SUPPLEMENTARY_SOPS", content)
        self.assertTrue("bán lẻ" in content.lower() and "dịch vụ" in content.lower())
        self.assertIn("7", content)
        self.assertIn("17", content)

    def test_production_deployment_runbook_content(self):
        """Verify Gates 90-97 coverage in the deployment runbook."""
        doc_path = self.docs_dir / "HO_SO_VAN_HANH_HA_TANG_PRODUCTION_VA_DEPLOYMENT_RUNBOOK.md"
        content = doc_path.read_text(encoding="utf-8")
        
        gates = [90, 91, 92, 93, 94, 95, 96, 97]
        for g in gates:
            self.assertTrue(
                f"Gate {g}" in content or f"Cổng {g}" in content or f"Mục {g}" in content,
                f"Runbook must cover Gate/Cổng/Mục {g}"
            )
            
        # Key technical topics
        self.assertIn("Render", content)
        self.assertIn("pip-audit", content)
        self.assertIn("bandit", content)
        self.assertIn("Brevo", content)
        self.assertTrue("worker" in content.lower() or "background" in content.lower())
        self.assertIn("Sentry", content)
        self.assertIn("pg_dump", content)
        self.assertIn("pg_restore", content)
        self.assertIn("SSL", content)

    def test_ci_workflow_quality_gates(self):
        """Verify GitHub Actions quality workflow contains security, audit, and test gates."""
        ci_path = self.root / ".github" / "workflows" / "quality.yml"
        self.assertTrue(ci_path.exists())
        ci_content = ci_path.read_text(encoding="utf-8")
        
        self.assertIn("pip-audit", ci_content)
        self.assertIn("bandit", ci_content)
        self.assertIn("coverage run", ci_content)
        self.assertIn("coverage report", ci_content)
        self.assertIn("postgis/postgis", ci_content)

    def test_security_middleware_configured(self):
        """Verify Security headers middleware and correlation middleware are configured."""
        self.assertIn("config.middleware.RequestCorrelationIdMiddleware", settings.MIDDLEWARE)
        self.assertIn("config.middleware.SecurityHeadersMiddleware", settings.MIDDLEWARE)
        self.assertIn("django.middleware.security.SecurityMiddleware", settings.MIDDLEWARE)
