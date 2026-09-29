"""Export blank human review forms or summarize filled forms, without DB writes."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from apps.knowledge.human_review import create_review, summarize_review


class Command(BaseCommand):
    help = "Export a blank RAG review form; --review summarizes a completed form. Never overwrites files."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--report", required=True)
        parser.add_argument("--review")
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        try:
            report = json.loads(Path(options["report"]).read_text(encoding="utf-8-sig"))
            if options["review"]:
                review = json.loads(Path(options["review"]).read_text(encoding="utf-8-sig"))
                result = summarize_review(report, review)
            else:
                result = create_review(report)
            serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
            with Path(options["output"]).open("x", encoding="utf-8") as stream:
                stream.write(serialized + "\n")
        except (OSError, ValueError, TypeError, AttributeError) as error:
            raise CommandError("Không thể xử lý phiếu chấm: kiểm tra cấu trúc JSON, rubric, fingerprint và đường dẫn; file đích phải chưa tồn tại.") from error
        self.stdout.write(self.style.SUCCESS("Đã xuất kết quả chấm; không gọi AI hoặc ghi database."))
