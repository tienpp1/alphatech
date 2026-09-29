import copy
from django.test import SimpleTestCase
from apps.knowledge.human_review import prepare_adversarial_review, create_review, summarize_review


class RAGReviewPacketTests(SimpleTestCase):
    def setUp(self):
        self.raw = {'details': [
            {'id': 'same', 'question': 'Q1', 'status': 'ANSWERED', 'response': {'answer': 'A1'}, 'fixture_documents': [{'text': 'Reference'}]},
            {'id': 'same', 'question': 'Q2', 'status': 'ANSWERED', 'response': {'answer': 'A2'}},
            {'id': 'denied', 'question': 'Private?', 'status': 'DENIED'},
        ]}

    def test_duplicate_fixture_ids_do_not_drop_paraphrase(self):
        report = prepare_adversarial_review(self.raw)
        self.assertEqual([r['id'] for r in report['details']], ['same@1', 'same@2'])
        self.assertEqual(len(report['excluded_cases']), 1)

    def test_blank_reviews_never_infer_quality(self):
        report = prepare_adversarial_review(self.raw)
        review = create_review(report)
        self.assertEqual(review['reviews'][0]['reference_documents'], [{'text': 'Reference'}])
        summary = summarize_review(report, review)
        self.assertEqual(summary['reviewed_cases'], 0)
        self.assertEqual(summary['unreviewed_cases'], 2)
        self.assertIsNone(summary['pass_rate_reviewed_percent'])

    def test_missing_actual_output_is_not_invented(self):
        for value in [None, {}, {'answer': ''}]:
            raw = copy.deepcopy(self.raw)
            raw['details'][0]['response'] = value
            with self.assertRaises(ValueError):
                prepare_adversarial_review(raw)

    def test_changed_reference_invalidates_review(self):
        report = prepare_adversarial_review(self.raw)
        review = create_review(report)
        report['details'][0]['reference_documents'][0]['text'] = 'Changed'
        with self.assertRaises(ValueError):
            summarize_review(report, review)
