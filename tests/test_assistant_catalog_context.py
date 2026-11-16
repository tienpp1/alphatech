"""Real routing and ORM-backed assistant context regressions; no live provider."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from apps.knowledge.intent_router import BusinessIntent, classify_business_intent


class CatalogLanguageRoutingTests(SimpleTestCase):
    ws = SimpleNamespace(workspace_type='RETAIL')

    def test_price_extrema_and_polite_variants_use_catalog_not_employee_or_sales(self):
        for query, order, limit in [
            ('cho tôi biết chiếc laptop có giá cao nhất', 'DESC', 1),
            ('laptop nao co gia cao nhat', 'DESC', 1),
            ('Cho tôi biết laptop nào rẻ nhất?', 'ASC', 1),
            ('Liệt kê top 3 laptop đắt nhất', 'DESC', 3),
            ('Top 2 điện thoại có giá thấp nhất', 'ASC', 2),
            ('Sản phẩm nào mắc nhất?', 'DESC', 1),
        ]:
            with self.subTest(query=query):
                result = classify_business_intent(query, self.ws)
                self.assertEqual(result['tools'], ['get_product_catalog_summary'])
                self.assertEqual(result['parameters']['sort_by'], 'unit_price')
                self.assertEqual(result['parameters']['sort_order'], order)
                self.assertEqual(result['parameters']['limit'], limit)

    def test_known_business_intents_are_not_hijacked_by_cho_toi_biet(self):
        for text, expected in [
            ('laptop nào bán chạy nhất tháng này?', 'get_top_selling_products'),
            ('doanh thu tháng này', 'get_sales_summary'),
            ('còn bao nhiêu laptop trong kho', 'get_stock_balance_summary'),
            ('có bao nhiêu laptop đang kinh doanh', 'get_product_catalog_summary'),
        ]:
            self.assertEqual(classify_business_intent('Cho tôi biết ' + text, self.ws)['tools'], [expected])
        for query in ['Ai biết sửa laptop?', 'Kỹ thuật viên nào có kỹ năng PostgreSQL?']:
            self.assertEqual(classify_business_intent(query, self.ws)['tools'], ['get_technician_skills_summary'])
        for query in ['Chính sách bảo hành laptop như thế nào?', 'Cho tôi biết quy trình nghỉ phép']:
            self.assertEqual(classify_business_intent(query, self.ws)['tools'], [])

    def test_budget_boundaries_are_exact_and_not_confused_with_sales(self):
        result = classify_business_intent('Tìm laptop dưới 20 triệu', self.ws)
        self.assertEqual(result['tools'], ['get_product_catalog_summary'])
        self.assertEqual(Decimal(result['parameters']['max_price']), Decimal('20000000'))
        self.assertFalse(result['parameters']['max_price_inclusive'])
        result = classify_business_intent('Laptop từ 10 triệu đến 20,5 triệu', self.ws)
        self.assertEqual(Decimal(result['parameters']['min_price']), Decimal('10000000'))
        self.assertEqual(Decimal(result['parameters']['max_price']), Decimal('20500000'))
        self.assertTrue(result['parameters']['max_price_inclusive'])
        self.assertEqual(classify_business_intent('Laptop nào có doanh thu cao nhất?', self.ws)['intent'], BusinessIntent.TOP_REVENUE_PRODUCTS)

    def test_named_product_price_uses_name_or_sku_filter(self):
        for query in ['Laptop ThinkPad X1 giá bao nhiêu?', 'Cho tôi biết giá của laptop ThinkPad X1 là bao nhiêu?']:
            with self.subTest(query=query):
                result = classify_business_intent(query, self.ws)
                self.assertEqual(result['tools'], ['get_product_catalog_summary'])
                self.assertIn('ThinkPad X1', result['parameters']['search'])

    def test_ranking_and_intersected_budgets_preserve_every_condition(self):
        result = classify_business_intent('Top 3 laptop đắt nhất dưới 20 triệu và trên 10 triệu', self.ws)
        params = result['parameters']
        self.assertEqual(params['sort_order'], 'DESC')
        self.assertEqual(params['limit'], 3)
        self.assertEqual(Decimal(params['min_price']), Decimal('10000000'))
        self.assertEqual(Decimal(params['max_price']), Decimal('20000000'))
        self.assertFalse(params['min_price_inclusive'])
        self.assertFalse(params['max_price_inclusive'])
        result = classify_business_intent('Laptop Dell XPS dưới 20 triệu', self.ws)
        self.assertEqual(result['parameters']['search'], 'Dell XPS')
        for query in ['Laptop dưới 20 USD', 'Laptop dưới 10 triệu và trên 20 triệu', 'Laptop đắt nhất và rẻ nhất', 'Laptop rẻ nhất không phải ASUS']:
            with self.subTest(query=query):
                self.assertEqual(classify_business_intent(query, self.ws)['intent'], BusinessIntent.AMBIGUOUS)

    def test_unsupported_conditions_and_mixed_metrics_require_clarification(self):
        for query in ['Laptop rẻ nhất RAM 32GB', 'Laptop đắt nhất còn hàng ở Quận 7',
                      'Laptop nào có giá cao nhất và bán chạy nhất?', 'Laptop bán chạy nhất dưới 20 triệu', 'Tìm laptop dưới 20']:
            with self.subTest(query=query):
                result = classify_business_intent(query, self.ws)
                self.assertEqual(result['intent'], BusinessIntent.AMBIGUOUS)
                self.assertEqual(result['tools'], [])

    def test_price_followup_keeps_tool_and_full_new_question_overrides_history(self):
        previous = classify_business_intent('Laptop có giá cao nhất?', self.ws)
        result = classify_business_intent('Còn rẻ nhất thì sao?', self.ws, [previous])
        self.assertEqual(result['tools'], ['get_product_catalog_summary'])
        self.assertEqual(result['parameters']['category'], 'laptop')
        self.assertEqual(result['parameters']['sort_order'], 'ASC')
        result = classify_business_intent('Còn ASUS thì sao?', self.ws, [previous])
        self.assertEqual(result['tools'], ['get_product_catalog_summary'])
        self.assertEqual(result['parameters']['search'].lower(), 'asus')
        result = classify_business_intent('Cho tôi biết doanh thu tháng này', self.ws, [previous])
        self.assertEqual(result['tools'], ['get_sales_summary'])
        result = classify_business_intent('Cái đó còn hàng không?', self.ws, [previous])
        self.assertEqual(result['intent'], BusinessIntent.AMBIGUOUS)

    def test_followup_replaces_brand_and_category_together(self):
        previous = classify_business_intent('Laptop ASUS đắt nhất?', self.ws)
        for query, category, brand in [('Còn Dell rẻ nhất thì sao?', 'laptop', 'dell'),
                                        ('Còn điện thoại Samsung thì sao?', 'smartphone', 'samsung')]:
            with self.subTest(query=query):
                result = classify_business_intent(query, self.ws, [previous])
                self.assertEqual(result['parameters']['category'], category)
                self.assertIn(brand, result['parameters']['search'].lower())
        result = classify_business_intent('Còn laptop giá dưới 20 triệu thì sao?', self.ws, [previous])
        self.assertEqual(Decimal(result['parameters']['max_price']), Decimal('20000000'))
        self.assertEqual(result['parameters']['search'].lower(), 'asus')
        self.assertEqual(result['parameters']['sort_order'], 'DESC')
        result = classify_business_intent('Còn trên 10 triệu thì sao?', self.ws, [result])
        self.assertEqual(Decimal(result['parameters']['min_price']), Decimal('10000000'))
        self.assertFalse(result['parameters']['max_price_inclusive'])

    def test_time_followup_preserves_ranking_tool(self):
        previous = classify_business_intent('Laptop bán chạy nhất tháng này?', self.ws)
        result = classify_business_intent('Tháng trước thì thế nào?', self.ws, [previous])
        self.assertEqual(result['tools'], ['get_top_selling_products'])
        self.assertEqual(result['parameters']['time_label'], 'tháng trước')

    def test_unsupported_followup_conditions_are_not_converted_to_literal_search(self):
        previous = classify_business_intent('Laptop ASUS đắt nhất?', self.ws)
        for query in ['Còn laptop RAM 32GB thì sao?', 'Còn laptop còn hàng thì sao?', 'Còn ASUS và Dell thì sao?']:
            with self.subTest(query=query):
                self.assertEqual(classify_business_intent(query, self.ws, [previous])['intent'], BusinessIntent.AMBIGUOUS)

    def test_explicit_followup_sort_is_not_a_name_or_inherited_order(self):
        previous = classify_business_intent('Laptop ASUS đắt nhất?', self.ws)
        for query, order in [('Còn giá tăng dần thì sao?', 'ASC'), ('Còn giá từ thấp đến cao thì sao?', 'ASC'),
                             ('Còn giá giảm dần thì sao?', 'DESC'), ('Còn giá từ cao đến thấp thì sao?', 'DESC')]:
            with self.subTest(query=query):
                result = classify_business_intent(query, self.ws, [previous])
                self.assertEqual(result['parameters']['sort_order'], order)
                self.assertEqual(result['parameters']['search'].lower(), 'asus')


@override_settings(LLM_GENERATION_PROVIDER='gemini', LLM_API_KEY='', GEMINI_API_KEY='')
class CatalogAssistantFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from apps.accounts.models import User
        from apps.workspaces.models import Workspace
        from apps.retail.models import Category, Product
        cls.user = User.objects.create_superuser('catalog-admin', 'admin@example.test', 'test-only')
        cls.other = User.objects.create_superuser('other-admin', 'other@example.test', 'test-only')
        cls.ws = Workspace.objects.create(code='catalog-chat', name='Catalog Chat', workspace_type='RETAIL')
        category = Category.objects.create(workspace=cls.ws, code='laptop', name='Laptop')
        for sku, name, price in [('A', 'Alpha Laptop', '10000000.25'), ('Z', 'ThinkPad X1', '30000000.75')]:
            Product.objects.create(workspace=cls.ws, category=category, sku=sku, name=name, unit_price=price)

    def test_exact_reported_query_answers_from_real_catalog_without_documents(self):
        from apps.knowledge.services import answer_grounded_query
        with patch('apps.knowledge.services.search_relevant_chunks') as retrieval:
            result = answer_grounded_query(self.ws, self.user, 'cho tôi biết chiếc laptop có giá cao nhất')
        retrieval.assert_not_called()
        self.assertIn('ThinkPad X1', result['answer'])
        self.assertIn('30,000,000.75', result['answer'])
        self.assertEqual(result['tools_used'][0]['tool'], 'get_product_catalog_summary')
        self.assertEqual(result['generation_metadata']['mode'], 'DETERMINISTIC')

    def test_actual_followup_excludes_current_message_and_preserves_category(self):
        from apps.knowledge.services import answer_grounded_query
        first = answer_grounded_query(self.ws, self.user, 'Laptop nào có giá cao nhất?')
        second = answer_grounded_query(self.ws, self.user, 'Còn rẻ nhất thì sao?', session_id=first['session_id'])
        self.assertIn('Alpha Laptop', second['answer'])
        self.assertIn('10,000,000.25', second['answer'])
        self.assertNotIn('30,000,000.75', second['answer'])
        foreign = answer_grounded_query(self.ws, self.other, 'Còn rẻ nhất thì sao?', session_id=first['session_id'])
        self.assertNotEqual(foreign['session_id'], first['session_id'])
        self.assertNotIn('Alpha Laptop', foreign['answer'])

    def test_groq_receives_scoped_price_facts_instead_of_employee_data(self):
        from apps.knowledge.services import answer_grounded_query
        with override_settings(LLM_GENERATION_PROVIDER='groq', GROQ_API_KEY='test-only-placeholder'):
            with patch('apps.knowledge.groq_generation.generate_groq_answer', return_value=('Catalog grounded reply', None)) as provider:
                result = answer_grounded_query(self.ws, self.user, 'Laptop nào đắt nhất?')
        context = provider.call_args.kwargs['context']
        self.assertEqual(context['tools_data'][0]['ranked_products'][0]['unit_price'], '30000000.75')
        self.assertEqual(context['tools_data'][0]['ranked_products'][0]['sku'], 'Z')
        self.assertEqual(result['generation_metadata']['provider'], 'groq')

    def test_smalltalk_uses_no_business_retrieval_or_provider(self):
        from apps.knowledge.services import answer_grounded_query
        with patch('apps.knowledge.services.search_relevant_chunks') as retrieval:
            with patch('apps.knowledge.groq_generation.generate_groq_answer') as provider:
                result = answer_grounded_query(self.ws, self.user, 'Xin chào')
        retrieval.assert_not_called()
        provider.assert_not_called()
        self.assertIn('chào', result['answer'].lower())
        self.assertEqual(result['tools_used'], [])
        self.assertEqual(result['generation_metadata']['reason'], 'SMALL_TALK')

    def test_denied_catalog_access_explains_permission_instead_of_missing_documents(self):
        from apps.accounts.models import Permission, Role, User
        from apps.workspaces.models import WorkspaceMembership
        from apps.knowledge.services import answer_grounded_query
        user = User.objects.create_user('chat-only')
        permission, _ = Permission.objects.get_or_create(codename='ai.chat', defaults={'name':'AI chat', 'module':'ai'})
        role = Role.objects.create(name='CHAT_WITHOUT_CATALOG')
        role.permissions.add(permission)
        WorkspaceMembership.objects.create(user=user, workspace=self.ws, role=role)
        with patch('apps.knowledge.groq_generation.generate_groq_answer') as provider:
            result = answer_grounded_query(self.ws, user, 'Laptop nào có giá cao nhất?')
        provider.assert_not_called()
        self.assertIn('quyền', result['answer'])
        self.assertEqual(result['tools_used'][0]['status'], 'PERMISSION_DENIED')
        self.assertEqual(result['generation_metadata']['reason'], 'PERMISSION_DENIED')
