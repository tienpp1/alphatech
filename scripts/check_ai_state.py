import os
import sys
import django

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.workspaces.models import Workspace
from apps.knowledge.models import KnowledgeBase, Document, DocumentChunk
from apps.accounts.models import User

print("=== WORKSPACES ===")
for ws in Workspace.objects.all():
    print(f"[{ws.id}] {ws.code} | {ws.name} | Type: {ws.workspace_type}")

print("\n=== KNOWLEDGE BASES ===")
for kb in KnowledgeBase.objects.select_related("workspace").all():
    print(f"[{kb.id}] Workspace: {kb.workspace.code} | Name: {kb.name}")

print("\n=== DOCUMENTS ===")
for d in Document.objects.select_related("workspace", "knowledge_base").all():
    print(f"[{d.id}] Workspace: {d.workspace.code} | KB: {d.knowledge_base.name} | Title: {d.title} | Status: {d.status} | Chunks: {d.chunks.count()}")

print("\n=== DATA/KNOWLEDGE DIRECTORY FILES ===")
data_dir = os.path.join("data", "knowledge")
if os.path.exists(data_dir):
    for f in os.listdir(data_dir):
        fp = os.path.join(data_dir, f)
        print(f" - {f} ({os.path.getsize(fp)} bytes)")
