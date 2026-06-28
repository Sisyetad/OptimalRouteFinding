import logging
import os
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class InfrastructureConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'infrastructure'

    def ready(self):
        if "test" in sys.argv:
            return

        if any(command in sys.argv for command in ["migrate", "makemigrations", "collectstatic", "shell"]):
            return

        if os.environ.get("RUN_MAIN") == "false":
            return

        try:
            from .bootstrap import load_initial_fuel_data

            load_initial_fuel_data()
        except Exception:
            logger.exception("Failed to load initial fuel data during startup")
