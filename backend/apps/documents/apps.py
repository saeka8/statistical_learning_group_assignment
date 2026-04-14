from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.documents"

    def ready(self):
        # Create the MinIO bucket on startup if it doesn't exist yet.
        # Wrapped in a broad except so tests and management commands that run
        # without MinIO available don't crash.
        try:
            from apps.documents.storage import ensure_bucket_exists
            ensure_bucket_exists()
        except Exception:
            pass
