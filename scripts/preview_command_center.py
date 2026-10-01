"""Render the demonstration template for visual QA without business DB writes."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['SENTRY_DSN'] = ''
import django
django.setup()
from django.template.loader import render_to_string

destination = ROOT / 'output' / 'command_center_qa'
destination.mkdir(parents=True, exist_ok=True)
(destination / 'index.html').write_text(render_to_string('dashboard/ai_command_center.html'), encoding='utf-8')
print(destination / 'index.html')
