"""
Unit & Integration Tests for SSRF Defense, Network Restrictions, and Upload Hardening.
"""

from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.integration.models import DataSource, SourceType, ImportStatus, EntityType
from apps.integration.parsers.api_parser import fetch_and_parse_api, validate_safe_remote_url
from apps.integration.services import execute_import_job, generate_import_preview
from apps.integration.serializers import DataSourceSerializer


class SSRFAndSecurityHardeningTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="sec_admin", email="sec_admin@example.com", password="AdminPass123!")
        self.role = Role.objects.create(name="ADMIN", description="Admin")
        self.ws = Workspace.objects.create(name="Sec WS", code="sec-ws", workspace_type=WorkspaceType.RETAIL)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role=self.role, is_default=True)
        self.client.force_login(self.user)

    def test_ssrf_rejects_localhost_and_loopback(self):
        targets = [
            "http://localhost:8000/api/v1/retail/orders/",
            "http://127.0.0.1:8000/api/v1/retail/orders/",
            "http://127.0.0.2:9000/secret",
            "http://[::1]:8080/data",
            "http://0.0.0.0:8000/",
        ]
        for target in targets:
            is_safe, error = validate_safe_remote_url(target)
            self.assertFalse(is_safe, f"Target '{target}' should have been blocked by SSRF validation.")
            self.assertIn("blocked", error.lower())

            res = fetch_and_parse_api(target)
            self.assertFalse(res["is_valid"])
            self.assertIn("Security Validation Error", res["error_message"])

    def test_ssrf_rejects_private_and_link_local_ips(self):
        targets = [
            "http://10.0.0.1/internal-feed",
            "http://192.168.1.100:8080/data.json",
            "http://172.16.0.5/api",
            "http://169.254.169.254/latest/meta-data/",
            "http://100.64.0.1/cgnat-secret",
        ]
        for target in targets:
            is_safe, error = validate_safe_remote_url(target)
            self.assertFalse(is_safe, f"Private IP '{target}' should have been blocked.")
            res = fetch_and_parse_api(target)
            self.assertFalse(res["is_valid"])

    def test_ssrf_rejects_cloud_metadata_hostnames_and_internal_suffixes(self):
        targets = [
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://instance-data/latest/meta-data/",
            "http://metadata.azure.com/metadata/instance",
            "http://internal-service.local/data.json",
            "http://server.internal/feed",
            "http://database.corp/export",
        ]
        for target in targets:
            is_safe, error = validate_safe_remote_url(target)
            self.assertFalse(is_safe, f"Internal host '{target}' should have been blocked.")

    def test_ssrf_rejects_forbidden_schemes(self):
        targets = [
            "file:///etc/passwd",
            "ftp://files.example.com/data.csv",
            "gopher://127.0.0.1:6379",
            "dict://127.0.0.1:11211",
        ]
        for target in targets:
            is_safe, error = validate_safe_remote_url(target)
            self.assertFalse(is_safe, f"Non-HTTP scheme '{target}' should have been blocked.")
            self.assertIn("forbidden url scheme", error.lower())

    def test_mock_relative_url_is_allowed(self):
        # Valid relative URL starting with /
        res = fetch_and_parse_api("/api/v1/mock-external/retail/orders/")
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["total_rows"], 5)

        # Scheme-relative URL (//) must be blocked
        res_scheme_rel = fetch_and_parse_api("//evil.com/data.json")
        self.assertFalse(res_scheme_rel["is_valid"])

    def test_file_upload_rejects_dangerous_extensions(self):
        ds = DataSource.objects.create(workspace=self.ws, name="Test DS", source_type=SourceType.CSV, created_by=self.user)

        for dangerous_name in ("malware.exe", "backdoor.py", "shell.sh", "index.php", "exploit.js"):
            file_obj = SimpleUploadedFile(dangerous_name, b"print('hacked')", content_type="text/plain")

            # 1. Preview rejected
            preview = generate_import_preview(file_obj=file_obj, source_type=SourceType.CSV)
            self.assertFalse(preview["is_valid"])
            self.assertIn("Unsupported file extension", preview["error_message"])

            # 2. Execution rejected with FAILED state
            job = execute_import_job(workspace=self.ws, user=self.user, data_source=ds, file_obj=file_obj)
            self.assertEqual(job.status, ImportStatus.FAILED)
            self.assertIn("SECURITY_VALIDATION_ERROR", job.error_summary[0]["error_type"])

    def test_file_upload_rejects_oversized_file(self):
        ds = DataSource.objects.create(workspace=self.ws, name="Oversized DS", source_type=SourceType.CSV, created_by=self.user)
        # Create a file object with size reported as 11 MB
        oversized_bytes = b"col1,col2\nval1,val2\n"
        file_obj = SimpleUploadedFile("huge.csv", oversized_bytes, content_type="text/csv")
        file_obj.size = 11 * 1024 * 1024  # 11 MB

        preview = generate_import_preview(file_obj=file_obj, source_type=SourceType.CSV)
        self.assertFalse(preview["is_valid"])
        self.assertIn("exceeds maximum allowed limit of 10 MB", preview["error_message"])

        job = execute_import_job(workspace=self.ws, user=self.user, data_source=ds, file_obj=file_obj)
        self.assertEqual(job.status, ImportStatus.FAILED)
        self.assertIn("10 MB", job.error_summary[0]["message"])

    def test_datasource_serializer_masks_credentials(self):
        ds = DataSource.objects.create(
            workspace=self.ws,
            name="Secure Feed",
            source_type=SourceType.MOCK_API,
            connection_config={
                "url": "/api/v1/mock-external/retail/orders/",
                "api_key": "sk-secret-token-value-9999",
                "auth_password": "SuperSecretPassword123!",
                "safe_param": "regular_value",
            },
            created_by=self.user,
        )
        serializer = DataSourceSerializer(ds)
        data = serializer.data
        cfg = data["connection_config"]

        self.assertNotEqual(cfg["api_key"], "sk-secret-token-value-9999")
        self.assertIn("******", cfg["api_key"])
        self.assertNotEqual(cfg["auth_password"], "SuperSecretPassword123!")
        self.assertIn("******", cfg["auth_password"])
        self.assertEqual(cfg["safe_param"], "regular_value")
