"""Rendered navigation/evidence contracts; no business database access."""
from html.parser import HTMLParser
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class PageElements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids = {}
        self.menu_links = {}
        self.div_depth = 0
        self.menus = []
        self.in_head = False
        self.in_style = False
        self.head_css = ""
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids[attrs["id"]] = attrs
        if tag == "div":
            self.div_depth += 1
            if attrs.get("role") == "menu":
                self.menus.append((self.div_depth, attrs.get("id")))
                self.menu_links[attrs.get("id")] = []
        if tag == "a" and self.menus:
            self.menu_links[self.menus[-1][1]].append(attrs.get("href"))
        if tag == "head":
            self.in_head = True
        if tag == "style":
            self.in_style = True

    def handle_endtag(self, tag):
        if tag == "div":
            if self.menus and self.menus[-1][0] == self.div_depth:
                self.menus.pop()
            self.div_depth -= 1
        if tag == "head":
            self.in_head = False
        if tag == "style":
            self.in_style = False

    def handle_data(self, text):
        if self.in_head and self.in_style:
            self.head_css += text


class DecisionSupportUITests(SimpleTestCase):
    def render_page(self, template="base.html", **extra):
        context = {
            "request": SimpleNamespace(user=SimpleNamespace(is_authenticated=True, username="manager")),
            "active_workspace": SimpleNamespace(id="test-workspace", name="TEST", code="TEST"),
            "chart_data": {"metrics": {}, "quality": {}},
            "runs": [], "recommendations": [], "approval_requests": [],
        }
        context.update(extra)
        return render_to_string(template, context)

    def test_advanced_data_menu_removed_without_losing_ai_routes(self):
        html = self.render_page()
        page = PageElements(html)
        self.assertNotIn("menu-dropdown-data", page.menu_links)
        self.assertNotIn("btn-dropdown-data", page.ids)
        self.assertEqual(page.menu_links["menu-dropdown-ai"], [
            "/noibo/ai/", "/noibo/knowledge/", "/noibo/forecasting/",
            "/noibo/recommendations/", "/noibo/approvals/",
        ])
        self.assertNotIn("Quản lý dữ liệu nâng cao", html)
        self.assertNotIn("Dự báo XGBoost</a>", html)

    def test_removed_menu_stays_absent_on_data_pages(self):
        for active_nav in ("integration", "integration_sources", "mapping"):
            with self.subTest(active_nav=active_nav):
                page = PageElements(self.render_page(active_nav=active_nav))
                self.assertNotIn("btn-dropdown-data", page.ids)
                self.assertNotIn("active", page.ids["btn-dropdown-ai"].get("class", "").split())

    def test_ai_navigation_is_active_for_assistant_and_decision_pages(self):
        for active_nav in ("ai", "knowledge", "forecasting", "recommendations", "approvals"):
            with self.subTest(active_nav=active_nav):
                page = PageElements(self.render_page(active_nav=active_nav))
                self.assertIn("active", page.ids["btn-dropdown-ai"].get("class", "").split())

    def test_navigation_uses_real_paths_when_views_omit_active_nav(self):
        for path, button_id in (("/noibo/recommendations/", "btn-dropdown-ai"),
                                ("/noibo/approvals/", "btn-dropdown-ai")):
            with self.subTest(path=path):
                request = SimpleNamespace(path=path, user=SimpleNamespace(is_authenticated=True))
                page = PageElements(self.render_page(request=request))
                self.assertIn("active", page.ids[button_id].get("class", "").split())

    def test_dashboard_scope_card_removed_but_data_links_remain(self):
        html = self.render_page("dashboard/main.html", health={}, retail={}, service={}, ai={})
        self.assertNotIn("Phạm vi Quản trị Hợp nhất", html)
        self.assertNotIn("btn-quick-report", html)
        self.assertIn('href="/noibo/integration/"', html)
        self.assertIn('href="/noibo/mapping/"', html)

    def test_help_is_visible_on_all_five_pages_with_existing_destinations(self):
        cases = [
            ("integration/dashboard.html", "integration", "vùng đệm", "/noibo/mapping/"),
            ("mapping/dashboard.html", "mapping", "không gọi LLM", "/noibo/integration/"),
            ("forecasting/index.html", "forecasting", "không phải độ chính xác", "/noibo/recommendations/"),
            ("recommendations/index.html", "recommendations", "không thay đổi nghiệp vụ", "/noibo/approvals/"),
            ("approvals/index.html", "approvals", "thực thi thay đổi nghiệp vụ ngay", "/noibo/recommendations/"),
        ]
        for template, page_name, phrase, target in cases:
            with self.subTest(template=template):
                html = self.render_page(template)
                page = PageElements(html)
                self.assertEqual(page.ids.get("support-guide", {}).get("data-page"), page_name)
                self.assertIn(phrase, html)
                self.assertIn(f'href="{target}"', html)

    def test_recommendation_and_approval_styles_reach_rendered_head(self):
        for template, selector in (("recommendations/index.html", ".rec-container"),
                                   ("approvals/index.html", ".custom-table")):
            with self.subTest(template=template):
                self.assertIn(selector, PageElements(self.render_page(template)).head_css)

    def test_forecast_model_and_large_error_are_not_hidden_or_relabelled(self):
        html = self.render_page("forecasting/index.html", chart_data={
            "model_label": "MA7", "effective_model": "MA7", "run_id": 10,
            "metrics": {"mae": 33244018.34, "mape": 1268.1},
            "snapshot": {"status": "HISTORICAL", "message": "Dữ liệu lịch sử",
                         "period_end": "2026-09-08", "age_days": 70},
            "quality": {},
        })
        for value in ("MA7", "HISTORICAL", "2026-09-08", "1268", "không phải độ chính xác"):
            self.assertIn(value, html)
