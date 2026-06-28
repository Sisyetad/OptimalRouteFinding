import logging
from pathlib import Path

from django.core.management import call_command
from django.db import OperationalError

from infrastructure.models import FuelStationModel

logger = logging.getLogger(__name__)


def _get_fuel_station_model():
    return FuelStationModel


def load_initial_fuel_data(force=False):
    model = _get_fuel_station_model()

    try:
        if not force and model.objects.exists():
            logger.info("Fuel station data already present; skipping bootstrap load")
            return False
    except OperationalError:
        logger.info("Database is unavailable during startup; delaying fuel data load")
        return False

    csv_path = Path(__file__).resolve().parent.parent / "fuel-prices-for-be-assessment.csv"
    if not csv_path.exists():
        logger.warning("Fuel data CSV not found at %s", csv_path)
        return False

    logger.info("Loading initial fuel data from %s", csv_path)
    call_command("load_fuel_data", str(csv_path))
    return True
