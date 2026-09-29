"""Export declared Django model metadata without querying business data."""
import os
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["SENTRY_DSN"] = ""
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""


def main(destination):
    import django
    django.setup()
    from django.apps import apps
    from django.urls import get_resolver, URLResolver
    rows = []
    for model in sorted(apps.get_models(), key=lambda m: m._meta.label):
        if not model.__module__.startswith("apps."):
            continue
        fields = []
        for field in model._meta.local_fields + model._meta.local_many_to_many:
            related = field.remote_field
            fields.append({"name": field.name, "type": field.get_internal_type(),
                           "primary_key": field.primary_key, "null": field.null,
                           "unique": field.unique, "many_to_many": field.many_to_many,
                           "target": related.model._meta.label if related else None,
                           "on_delete": getattr(getattr(related, "on_delete", None), "__name__", None)})
        rows.append({"model": model._meta.label, "table": model._meta.db_table,
                     "fields": fields, "unique_together": model._meta.unique_together,
                     "constraints": [str(c) for c in model._meta.constraints]})
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    sources = list((ROOT / "apps").rglob("models.py")) + list((ROOT / "apps").glob("*/migrations/*.py"))
    manifest = {"scope": "Declared ORM metadata, not inspected database schema; no data queried",
                "models": rows, "source_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)}}
    (destination / "model_contract.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Hợp đồng model trích xuất từ mã nguồn", "", manifest["scope"], "",
             "Field null/unique là khai báo ORM. Ràng buộc tổ hợp/điều kiện phải đọc cùng constraints; không suy ra quyền truy cập từ FK.", ""]
    for row in rows:
        lines += ["## " + row["model"], "", "Table: `" + row["table"] + "`", "", "| Field | Type | Null | Unique | Target |", "|---|---|---|---|---|"]
        for f in row["fields"]:
            lines.append(f"| {f['name']} | {f['type']} | {f['null']} | {f['unique']} | {f['target'] or ''} |")
        lines += ["", "Unique together: `" + str(row["unique_together"]) + "`", "", "Constraints:"]
        lines += ["- `" + c + "`" for c in row["constraints"]] or ["- Không khai báo tại Meta.constraints."]
        lines += [""]
    (destination / "model_contract.md").write_text("\n".join(lines), encoding="utf-8")
    routes = []
    def walk(patterns, prefix=""):
        for pattern in patterns:
            route = prefix + str(pattern.pattern)
            if isinstance(pattern, URLResolver):
                walk(pattern.url_patterns, route)
            else:
                callback = pattern.callback
                view = getattr(callback, "view_class", callback)
                routes.append({"route": route, "name": pattern.name,
                               "view": view.__module__ + "." + view.__name__})
    walk(get_resolver().url_patterns)
    (destination / "routes.json").write_text(json.dumps(routes, indent=2, ensure_ascii=False), encoding="utf-8")
    for app_label in sorted({row["model"].split('.')[0] for row in rows}):
        diagram = ["erDiagram"]
        for row in rows:
            if not row["model"].startswith(app_label + '.'):
                continue
            entity = row['model'].replace('.', '_')
            diagram += ["    " + entity + " {"]
            diagram += [f"        {f['type']} {f['name']}" for f in row['fields']]
            diagram += ["    }"]
            for f in row['fields']:
                if not f['target']:
                    continue
                left = f['target'].replace('.', '_')
                cardinality = '}o--o{' if f['many_to_many'] else ('|o' if f['null'] else '||') + '--' + ('o|' if f['unique'] else 'o{')
                diagram.append(f'    {left} {cardinality} {entity} : "{f["name"]}"')
        (destination / (app_label + '.mmd')).write_text('\n'.join(diagram), encoding='utf-8')
    print(json.dumps({"models": len(rows), "destination": str(destination), "database_queries": "none issued by exporter"}))


if __name__ == "__main__":
    main(sys.argv[1])
