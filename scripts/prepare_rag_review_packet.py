"""Create a blank review packet from recorded observations, no model/DB calls."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apps.knowledge.human_review import prepare_adversarial_review, create_review, summarize_review


def main(source, destination):
    raw = json.loads(source.read_text(encoding='utf-8'))
    report = prepare_adversarial_review(raw)
    review = create_review(report)
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in [('report.json', report), ('review.json', review), ('initial_summary.json', summarize_review(report, review))]:
        (destination / name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'eligible_answers': len(report['details']), 'excluded_denials': len(report['excluded_cases']), 'graded': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    main(args.source, args.output)
