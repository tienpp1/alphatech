"""Create a blank review packet from recorded observations, no model/DB calls."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apps.knowledge.human_review import prepare_adversarial_review, create_review, summarize_review


def render_review_markdown(report):
    """Readable recorded evidence with blank judgments, never a generated grade."""
    lines = ['# Phiếu chấm câu trả lời RAG đã ghi nhận', '',
             'Chỉ chấm output dưới đây. Đúng sự thật / đúng số liệu / đủ ý / nguồn hỗ trợ:',
             'ghi Đạt hoặc Không đạt riêng từng tiêu chí, kèm lý do, tên người chấm và thời điểm.',
             'Không ghi PASS chung từ điểm keyword. Dữ liệu synthetic, không là chính sách thật.', '']
    for row in report['details']:
        lines += [f"## {row['id']}", '', f"Câu hỏi: {row.get('question')}", '',
                  'Câu trả lời thực tế:', '', str(row.get('answer', '')), '',
                  'Nguồn và thông tin chuẩn để đối chiếu:', '', '```json',
                  json.dumps({'reference_documents': row.get('reference_documents', []),
                              'expected': row.get('expected'), 'sources': row.get('sources', []),
                              'tools_used': row.get('tools_used', [])}, ensure_ascii=False, indent=2),
                  '```', '', 'Đánh giá: CHƯA CHẤM. Nhận xét: …', '']
    return '\n'.join(lines)


def main(source, destination, recorded_report=False):
    raw = json.loads(source.read_text(encoding='utf-8'))
    report = raw if recorded_report else prepare_adversarial_review(raw)
    review = create_review(report)
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in [('report.json', report), ('review.json', review), ('initial_summary.json', summarize_review(report, review))]:
        (destination / name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    (destination / 'review.md').write_text(render_review_markdown(report), encoding='utf-8')
    print(json.dumps({'eligible_answers': len(review['reviews']), 'excluded_denials': len(report.get('excluded_cases', [])), 'graded': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--recorded-report', action='store_true', help='Source is an existing benchmark report, not adversarial observations.')
    args = parser.parse_args()
    main(args.source, args.output, args.recorded_report)
