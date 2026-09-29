"""Checks document integrity only; not a functional acceptance percentage."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AcademicScopeContractTests(unittest.TestCase):
    def test_all_scope_requirements_are_traceable(self):
        scope = (ROOT / 'docs/ACADEMIC_ACCEPTANCE_SCOPE.md').read_text(encoding='utf-8')
        matrix = (ROOT / 'docs/ACADEMIC_REQUIREMENTS_MATRIX.md').read_text(encoding='utf-8')
        extract = lambda text: set(re.findall(r'^\| ([A-Z_]+) \|', text, re.M))
        self.assertEqual(len(extract(scope)), 12)
        self.assertEqual(extract(scope), extract(matrix))
        self.assertTrue({'TEAM_CHAT', 'BULLETIN'} <= extract(scope))

    def test_referenced_source_and_test_paths_exist(self):
        matrix = (ROOT / 'docs/ACADEMIC_REQUIREMENTS_MATRIX.md').read_text(encoding='utf-8')
        paths = re.findall(r'`((?:apps|tests)/[^`]+\.py)`', matrix)
        self.assertGreater(len(paths), 20)
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file(), path)

    def test_readme_links_to_current_scope(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertIn('Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI', readme)
        self.assertIn('docs/ACADEMIC_ACCEPTANCE_SCOPE.md', readme)
        self.assertIn('docs/ACADEMIC_REQUIREMENTS_MATRIX.md', readme)
