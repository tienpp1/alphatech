"""Regression guard for reviewed draft statements, not scientific validation."""
from pathlib import Path
from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = [
    'HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md', 'THUYET_MINH_DO_AN_CHUONG_1_VA_2.md',
    'THUYET_MINH_DO_AN_CHUONG_3_4_5.md', 'HOI_DONG_DEMO_GUIDE.md',
    'academic-defense-notes.md', 'ai-defense-guide.md', 'project-summary.md',
    'SLIDES_BAO_VE_KHOA_LUAN.html',
    'NEXT_CLOSURE_GATES.md', 'HO_SO_VAN_HANH_HA_TANG_PRODUCTION_VA_DEPLOYMENT_RUNBOOK.md',
    'HO_SO_DOI_CHIEU_TON_KHO_VA_FULFILLMENT.md',
    'HO_SO_RA_SOAT_TAI_LIEU_SOP_VA_TRONG_TAM_NGHIEP_VU.md',
]


class AcademicCurrentClaimTests(SimpleTestCase):
    def test_withdrawn_positive_claims_do_not_return(self):
        banned = ['97 / 97 mục (đạt 100,0%)', 'Toàn bộ 97/97 mục đã được đóng hoàn toàn',
                  'Độ đúng đắn có căn cứ (100%)', 'chính xác tuyệt đối',
                  'Chứng minh tính bất khả xâm phạm', 'ngăn chặn triệt để lặp mã']
        banned += ['ĐÓNG HOÀN TOÀN (CLOSED)', 'Toàn bộ 97 / 97 mục trong checklist đã được đóng hoàn toàn']
        banned += ['97 / 97 (100.0%) TIÊU CHÍ ĐÃ ĐÓNG HOÀN TOÀN', 'Khách hàng tuyệt đối không lọt']
        banned += ['Các bản ghi này tuyệt đối không thể sửa hoặc xóa']
        for name in ACTIVE:
            text = (ROOT / 'docs' / name).read_text(encoding='utf-8')
            for phrase in banned:
                with self.subTest(file=name, phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_current_status_section_uses_ledger_not_old_closure(self):
        text = (ROOT / 'docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md').read_text(encoding='utf-8')
        current = text.split('### 4.1 ', 1)[1].split('### 4.2 ', 1)[0]
        self.assertIn('CHECKLIST_97_PROGRESS.md', current)
        self.assertIn('đã bị thu hồi', current)
        self.assertNotIn('Closed with Full Evidence', current)

    def test_project_context_has_current_contact_and_rbac_contract(self):
        text = (ROOT / 'docs/PROJECT_CONTEXT.md').read_text(encoding='utf-8')
        self.assertNotIn('there is no Contact model', text)
        self.assertNotIn('Contact has no persistent entity', text)
        self.assertNotIn('knowledge UI calls built-in', text)

    def test_draft_progress_not_old_hardcoded_value(self):
        text = (ROOT / 'docs/THUYET_MINH_DO_AN_CHUONG_3_4_5.md').read_text(encoding='utf-8')
        self.assertNotIn('71/97 (73,2%)', text)
        self.assertNotIn('26 mục, xem CHECKLIST', text)
