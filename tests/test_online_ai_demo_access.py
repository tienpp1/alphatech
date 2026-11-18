"""The demonstration uses current internal access and never mutates domain data."""
from datetime import datetime
from unittest.mock import patch

from django.db import connection
from django.test import Client, RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext

from apps.accounts.internal_access import AUTH_METHOD_KEY
from apps.accounts.models import Permission, Role, User
from apps.forecasting.demo_lab import DEMO_CASES
from apps.public_web.models import SocialIdentity
from apps.workspaces.models import Workspace, WorkspaceMembership
from tests.test_decision_support_ui import PageElements


LAB = "/noibo/mo-phong-ai/"
RUN = LAB + "run/"
FORM = "application/x-www-form-urlencoded"


class OnlineAiDemoAccessTests(TestCase):
    def test_real_research_requires_current_retail_scope_csrf_and_does_not_write(self):
        endpoint = LAB + 'doanh-thu-xgboost/?workspace_id=' + str(self.primary.pk)
        client = self.client_for(self.user, csrf=True)
        response = client.get(LAB)
        self.assertEqual(response.status_code, 200)
        token = client.cookies['csrftoken'].value
        with patch('apps.forecasting.revenue_research.evaluate_revenue_xgboost', return_value={'data_mode': 'EXPERIMENTAL_NOT_OPERATIONAL'}) as evaluate:
            self.assert_status_no_store(client.post(endpoint, 'run=1', content_type=FORM), 403)
            self.assert_status_no_store(client.post(endpoint, 'run=1&extra=1', content_type=FORM, HTTP_X_CSRFTOKEN=token), 400)
            result = client.post(endpoint, 'run=1', content_type=FORM, HTTP_X_CSRFTOKEN=token)
            self.assert_status_no_store(result, 200)
            self.assertEqual(result.json()['data_mode'], 'EXPERIMENTAL_NOT_OPERATIONAL')
            evaluate.assert_called_once()
            evaluate.reset_mock()
            result = client.post(endpoint, 'run=1', content_type=FORM, HTTP_X_CSRFTOKEN=token,
                                 HTTP_X_WORKSPACE_ID=str(self.secondary.pk))
            self.assert_status_no_store(result, 403)
            evaluate.assert_not_called()

    @classmethod
    def setUpTestData(cls):
        permission, _ = Permission.objects.get_or_create(
            codename="forecasting.manage_forecast",
            defaults={"name": "Manage forecast", "module": "forecasting"},
        )
        cls.manager, _ = Role.objects.get_or_create(name="MANAGER")
        cls.admin, _ = Role.objects.get_or_create(name="ADMIN")
        cls.employee, _ = Role.objects.get_or_create(name="EMPLOYEE")
        for role in (cls.manager, cls.admin, cls.employee):
            role.permissions.add(permission)
        cls.permission = permission
        cls.primary = Workspace.objects.create(name="Workspace A", code="demo-a", workspace_type="RETAIL")
        cls.secondary = Workspace.objects.create(name="Workspace B", code="demo-b", workspace_type="SERVICE")
        cls.foreign = Workspace.objects.create(name="Workspace C", code="demo-c", workspace_type="RETAIL")
        cls.user = cls.make_user("lab-manager")
        cls.primary_member = WorkspaceMembership.objects.create(
            user=cls.user, workspace=cls.primary, role=cls.manager, is_default=True,
        )
        cls.secondary_member = WorkspaceMembership.objects.create(
            user=cls.user, workspace=cls.secondary, role=cls.employee,
        )

    @classmethod
    def make_user(cls, username, **kwargs):
        return User.objects.create_user(username=username, email=f"{username}@example.test", **kwargs)

    def client_for(self, user=None, *, csrf=False, workspace=None, method="password"):
        client = Client(enforce_csrf_checks=csrf)
        if user:
            client.force_login(user)
            session = client.session
            session[AUTH_METHOD_KEY] = method
            if workspace is not None:
                session["active_workspace_id"] = str(workspace.pk)
            session.save()
        return client

    def post(self, client, body="case=retrieval", *, endpoint=RUN, **kwargs):
        return client.post(endpoint, body, content_type=FORM, **kwargs)

    def assert_status_no_store(self, response, status):
        self.assertEqual(response.status_code, status)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))

    def assert_denied(self, client, **kwargs):
        self.assert_status_no_store(client.get(LAB, **kwargs), 403)
        self.assert_status_no_store(self.post(client, **kwargs), 403)

    def test_anonymous_denials_are_not_cacheable(self):
        client = self.client_for()
        self.assert_status_no_store(client.get(LAB), 302)
        self.assert_status_no_store(self.post(client), 403)

    def test_customer_and_google_identity_or_session_are_denied(self):
        customer = self.make_user("lab-customer")
        linked = self.make_user("lab-google", is_superuser=True)
        WorkspaceMembership.objects.create(user=linked, workspace=self.primary, role=self.manager)
        SocialIdentity.objects.create(provider="GOOGLE", subject="lab-google-subject", user=linked,
                                      provider_email=linked.email)
        for user, method in ((customer, "password"), (linked, "password"), (self.user, "google")):
            with self.subTest(user=user.username, session=method):
                self.assert_denied(self.client_for(user, method=method))
        self.assert_status_no_store(
            self.client_for(linked).get(LAB, HTTP_ACCEPT="text/html"), 403,
        )

    def test_employee_with_permission_cannot_use_manager_rights_from_another_workspace(self):
        client = self.client_for(self.user, workspace=self.secondary)
        self.assert_denied(client)
        self.assert_denied(self.client_for(self.user), HTTP_X_WORKSPACE_ID=str(self.secondary.pk))
        self.assert_denied(self.client_for(self.user), HTTP_X_WORKSPACE=self.foreign.code)
        # The same policy controls the link on other pages in the shared shell.
        response = client.get("/noibo/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, f'href="{LAB}"')

    def test_authorized_page_has_five_fixed_cases_shared_menu_and_no_computation(self):
        client = self.client_for(self.user)
        with patch("apps.forecasting.demo_views.run_demo_case") as run:
            response = client.get(LAB)
        self.assert_status_no_store(response, 200)
        run.assert_not_called()
        self.assertContains(response, f'href="{LAB}"')
        action = PageElements(response.content.decode()).ids["demo-form"]["action"]
        self.assertEqual(action, f"{RUN}?workspace_id={self.primary.pk}")
        self.assertContains(response, 'for="demo-case"')
        self.assertContains(response, "Workspace A")
        self.assertContains(response, "không ghi dữ liệu nghiệp vụ")
        self.assertContains(response, "không gọi dịch vụ AI")
        self.assertContains(response, "Kịch bản và dữ liệu mẫu đã biết trước.")
        self.assertContains(response, "Đây không phải kiểm thử mù hay bằng chứng thương mại.")
        for case in DEMO_CASES:
            self.assertContains(response, f'value="{case}"')

    def test_rendered_form_cannot_run_after_switch_to_another_eligible_workspace(self):
        WorkspaceMembership.objects.filter(pk=self.secondary_member.pk).update(role=self.manager)
        client = self.client_for(self.user, csrf=True, workspace=self.primary)
        response = client.get(LAB)
        self.assert_status_no_store(response, 200)
        action = PageElements(response.content.decode()).ids["demo-form"]["action"]
        csrf_header = {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value}
        self.assert_status_no_store(self.post(client, endpoint=action, **csrf_header), 200)
        session = client.session
        session["active_workspace_id"] = str(self.secondary.pk)
        session.save()
        self.assert_status_no_store(client.get(LAB), 200)
        with patch("apps.forecasting.demo_views.run_demo_case") as run:
            denied = self.post(client, endpoint=action, **csrf_header)
        self.assert_status_no_store(denied, 403)
        self.assertEqual(denied.json()["error"], "access_denied")
        run.assert_not_called()

    def test_admin_and_existing_superuser_need_current_verified_workspace(self):
        WorkspaceMembership.objects.filter(pk=self.primary_member.pk).update(role=self.admin)
        self.assert_status_no_store(self.client_for(self.user).get(LAB), 200)
        superuser = self.make_user("lab-super", is_superuser=True)
        client = self.client_for(superuser)
        self.assert_status_no_store(client.get(LAB, HTTP_X_WORKSPACE=self.primary.code), 200)
        self.assert_denied(client, HTTP_X_WORKSPACE_ID="not-a-uuid")
        Workspace.objects.filter(pk=self.primary.pk).update(is_active=False)
        self.assert_denied(client, HTTP_X_WORKSPACE_ID=str(self.primary.pk))
        from apps.forecasting.demo_views import can_use_ai_demo

        request = RequestFactory().get(LAB)
        request.user, request.session = superuser, {}
        self.assertFalse(can_use_ai_demo(request))
        request.active_workspace = self.primary  # stale active object
        self.assertFalse(can_use_ai_demo(request))

    def test_revoked_role_or_permission_does_not_remain_authorized(self):
        client = self.client_for(self.user, workspace=self.primary)
        self.assert_status_no_store(client.get(LAB), 200)
        self.manager.permissions.remove(self.permission)
        self.assert_denied(client)
        self.manager.permissions.add(self.permission)
        WorkspaceMembership.objects.filter(pk=self.primary_member.pk).update(is_active=False)
        self.assert_denied(client)

    def test_revoked_session_selection_uses_canonical_default_not_lab_owned_selection(self):
        client = self.client_for(self.user, workspace=self.secondary)
        WorkspaceMembership.objects.filter(pk=self.secondary_member.pk).update(is_active=False)
        response = client.get(LAB)
        self.assert_status_no_store(response, 200)
        self.assertEqual(response.context["active_workspace"].pk, self.primary.pk)
        self.assertEqual(client.session["active_workspace_id"], str(self.primary.pk))

    def test_invalid_explicit_selectors_never_fall_back(self):
        client = self.client_for(self.user, workspace=self.primary)
        primary_id = str(self.primary.pk)
        for headers in (
            {"HTTP_X_WORKSPACE_ID": ""}, {"HTTP_X_WORKSPACE_ID": " "},
            {"HTTP_X_WORKSPACE_ID": "invalid"}, {"HTTP_X_WORKSPACE": ""},
            {"HTTP_X_WORKSPACE": "invalid"},
            {"HTTP_X_WORKSPACE_ID": primary_id, "HTTP_X_WORKSPACE": ""},
            {"HTTP_X_WORKSPACE_ID": primary_id, "HTTP_X_WORKSPACE": self.secondary.code},
            {"HTTP_X_WORKSPACE_ID": primary_id, "HTTP_X_WORKSPACE": self.primary.code + ", " + self.secondary.code},
        ):
            with self.subTest(headers=headers):
                self.assert_denied(client, **headers)
        for query in ("workspace_id=", "workspace_id=not-a-uuid", "workspace=", "workspace=oops",
                      f"workspace_id={self.secondary.pk}", f"workspace_id={primary_id}&workspace_id={primary_id}",
                      f"workspace={self.secondary.pk}", f"workspace={primary_id}&workspace={primary_id}",
                      f"workspace_id={primary_id}&workspace={self.secondary.pk}"):
            with self.subTest(query=query):
                self.assert_status_no_store(client.get(LAB + "?" + query), 403)
                self.assert_status_no_store(self.post(client, endpoint=RUN + "?" + query), 403)
        self.assert_status_no_store(client.get(
            LAB + f"?workspace_id={primary_id}&workspace={primary_id}", HTTP_X_WORKSPACE_ID=primary_id,
            HTTP_X_WORKSPACE=self.primary.code,
        ), 200)

    def test_csrf_is_required_and_valid_token_can_be_sent_in_header_or_as_only_optional_field(self):
        client = self.client_for(self.user, csrf=True)
        self.assert_status_no_store(client.get(LAB), 200)
        token = client.cookies["csrftoken"].value
        self.assert_status_no_store(self.post(client), 403)
        self.assert_status_no_store(self.post(client, HTTP_X_CSRFTOKEN=token), 200)
        self.assert_status_no_store(self.post(client, f"case=retrieval&csrfmiddlewaretoken={token}"), 200)

    def test_strict_body_and_method_allowlists_reject_without_running_case(self):
        client = self.client_for(self.user)
        invalid_bodies = (
            "", "case=", "case=FORECAST", "case=forecast+", "case=%FF",
            "case=retrieval&case=forecast", "case=forecast&%63ase=forecast", "case=retrieval&x=1",
            "case=retrieval&workspace_id=demo-a", "case=retrieval&prompt=abc", "case=retrieval&upload=x",
            "case=retrieval&csrfmiddlewaretoken=x&csrfmiddlewaretoken=y",
            "case=retrieval&csrfmiddlewaretoken=x%ZZ", "case=retrieval&",
            "case=retrieval&csrfmiddlewaretoken=" + "x" * 512,
        )
        with patch("apps.forecasting.demo_views.run_demo_case") as run:
            for body in invalid_bodies:
                with self.subTest(body=body[:100]):
                    self.assert_status_no_store(self.post(client, body), 400)
            self.assert_status_no_store(client.post(RUN, '{"case":"retrieval"}', content_type="application/json"), 415)
            self.assert_status_no_store(client.post(RUN, {"case": "retrieval"}), 415)
            self.assert_status_no_store(self.post(client, endpoint=RUN + "?case=forecast"), 400)
            for endpoint, methods in ((LAB, ("POST", "HEAD", "PUT", "OPTIONS", "DELETE")),
                                      (RUN, ("GET", "HEAD", "PUT", "OPTIONS", "DELETE"))):
                for method in methods:
                    with self.subTest(endpoint=endpoint, method=method):
                        self.assert_status_no_store(client.generic(method, endpoint), 405)
            run.assert_not_called()

    def test_advertised_oversize_body_is_rejected_before_csrf_parser_reads_it(self):
        client = self.client_for(self.user, csrf=True)
        # No token. 400 instead of the normal 403 proves the length gate ran first.
        self.assert_status_no_store(self.post(client, CONTENT_LENGTH="513"), 400)

    def test_busy_and_safe_failure_do_not_leak_and_lock_recovers(self):
        client = self.client_for(self.user)
        from apps.forecasting import demo_views

        with demo_views._execution_lock:
            with patch.object(demo_views, "run_demo_case") as run:
                busy = self.post(client)
            run.assert_not_called()
        self.assert_status_no_store(busy, 409)
        self.assertEqual(busy.json()["error"], "busy")
        with patch.object(demo_views, "run_demo_case", side_effect=OSError("private-path/credential-marker")):
            failure = self.post(client)
        self.assert_status_no_store(failure, 503)
        self.assertEqual(failure.json()["error"], "unavailable")
        self.assertNotContains(failure, "credential-marker", status_code=503)
        self.assertNotIn("data", failure.json())
        self.assert_status_no_store(self.post(client), 200)

    def test_every_case_runs_real_components_and_never_writes_or_calls_provider(self):
        client = self.client_for(self.user)
        self.assert_status_no_store(client.get(LAB), 200)  # settle ordinary session selection
        forbidden = AssertionError("Demo must not contact a provider or train")
        with (patch("socket.socket.connect", side_effect=forbidden),
              patch("apps.forecasting.guarded.fit_guarded", side_effect=forbidden),
              patch("apps.forecasting.adaptive.fit_direct", side_effect=forbidden),
              CaptureQueriesContext(connection) as queries):
            results = {}
            for case in DEMO_CASES:
                with self.subTest(case=case):
                    response = self.post(client, "case=" + case)
                    self.assert_status_no_store(response, 200)
                    result = response.json()
                    self.assertEqual(set(result), {
                        "case", "scope", "execution_mode", "warnings", "data", "executed_at", "elapsed_seconds",
                    })
                    self.assertEqual((result["case"], result["scope"]), (case, "SYNTHETIC_DEMO"))
                    self.assertIsNotNone(datetime.fromisoformat(result["executed_at"]).tzinfo)
                    self.assertGreaterEqual(result["elapsed_seconds"], 0)
                    self.assertTrue(result["execution_mode"])
                    self.assertTrue(result["warnings"])
                    self.assertNotIn("booster", response.content.decode("utf-8"))
                    results[case] = result["data"]
        self.assertTrue(queries.captured_queries)
        self.assertTrue(all(q["sql"].lstrip().upper().startswith("SELECT ") for q in queries))
        self.assertAlmostEqual(results["forecast"]["metrics"]["xgboost"]["mae"], 896681.5191052415, delta=.01)
        self.assertEqual(results["retrieval"]["answer"], results["retrieval"]["candidates"][0]["excerpt"])
        self.assertEqual(results["mapping_pending"]["after"], {})
        self.assertIn("customer_id", results["mapping_confirmed"]["after"])
        self.assertTrue(results["mapping_confirmed"]["errors"])
        self.assertFalse(results["recommendation"]["tool"]["check_domain"])
