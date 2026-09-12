from django.apps import AppConfig


class PublicWebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public_web"
    verbose_name = "Public Business Website"

    def ready(self):
        from . import approval_notices  # noqa: F401
