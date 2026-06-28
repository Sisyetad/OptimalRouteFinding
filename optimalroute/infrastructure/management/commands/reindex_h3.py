import h3
from django.core.management.base import BaseCommand
from infrastructure.models import FuelStationModel
from infrastructure.repositories import DjangoFuelRepository


def _to_h3(lat: float, lon: float, resolution: int) -> str:
    if hasattr(h3, "latlng_to_cell"):
        return h3.latlng_to_cell(lat, lon, resolution)
    return h3.geo_to_h3(lat, lon, resolution)


class Command(BaseCommand):
    help = (
        "Recompute h3_index for every FuelStationModel row at the "
        "repository's current H3 resolution. Run this any time the "
        "resolution constant changes, or if rows were loaded by a path "
        "that used a different resolution (e.g. an old load_fuel_data run)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report how many rows would change without saving.",
        )

    def handle(self, *args, **options):
        resolution = DjangoFuelRepository.H3_RESOLUTION
        dry_run = options["dry_run"]

        self.stdout.write(f"Target H3 resolution: {resolution}")

        to_update = []
        checked = 0
        changed = 0

        for station in FuelStationModel.objects.all().iterator():
            checked += 1
            try:
                correct_idx = _to_h3(station.latitude, station.longitude, resolution)
            except Exception as exc:
                self.stdout.write(
                    self.style.WARNING(f"  skip id={station.id}: {exc}")
                )
                continue

            if station.h3_index != correct_idx:
                changed += 1
                station.h3_index = correct_idx
                to_update.append(station)

        self.stdout.write(f"Checked: {checked}  |  Needing update: {changed}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes saved."))
            return

        if to_update:
            FuelStationModel.objects.bulk_update(to_update, ["h3_index"], batch_size=1000)

        self.stdout.write(self.style.SUCCESS(f"✅ Re-indexed {changed} station(s)."))