from django.db import migrations


def install_append_only_trigger(apps, schema_editor):
    """Install database enforcement on PostgreSQL deployments.

    SQLite (used by the focused local test suite) has no compatible trigger
    syntax here; the model-level guard remains active there.  Production
    PostgreSQL receives a trigger so queryset UPDATE/DELETE cannot bypass the
    append-only invariant.
    """
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        CREATE OR REPLACE FUNCTION audit_auditlog_immutable()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_auditlog is append-only';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER audit_auditlog_no_update
        BEFORE UPDATE OR DELETE ON audit_auditlog
        FOR EACH ROW EXECUTE FUNCTION audit_auditlog_immutable();
        """
    )


def uninstall_append_only_trigger(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        DROP TRIGGER IF EXISTS audit_auditlog_no_update ON audit_auditlog;
        DROP FUNCTION IF EXISTS audit_auditlog_immutable();
        """
    )


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]
    operations = [
        migrations.RunPython(install_append_only_trigger, uninstall_append_only_trigger),
    ]
