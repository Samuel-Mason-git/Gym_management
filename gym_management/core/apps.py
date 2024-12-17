from django.apps import AppConfig
import threading
from .crons import auto_exit_cron_job


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Start the auto_exit_cron_job in a background thread
        thread = threading.Thread(target=auto_exit_cron_job, daemon=True)
        thread.start()