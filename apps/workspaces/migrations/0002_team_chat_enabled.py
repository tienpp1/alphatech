from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('workspaces', '0001_initial')]

    operations = [
        # Preserve existing employees' chat access without changing any messages.
        migrations.AddField(
            model_name='workspacemembership', name='team_chat_enabled',
            field=models.BooleanField(default=True, db_default=True),
        ),
        # Only historical rows inherit access. Every new membership opts in.
        migrations.AlterField(
            model_name='workspacemembership', name='team_chat_enabled',
            field=models.BooleanField(default=False, db_default=False),
        ),
    ]
