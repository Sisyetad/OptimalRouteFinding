import csv
import asyncio
import random
import h3
import aiohttp
from django.conf import settings
from django.core.management.base import BaseCommand
from infrastructure.models import FuelStationModel
from asgiref.sync import sync_to_async


class Command(BaseCommand):
    help = "Fast async CSV loader with Mapbox, idempotent + optimized"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str)
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--concurrency", type=int, default=10)

    def handle(self, *args, **options):
        asyncio.run(self.async_handle(options))

    async def async_handle(self, options):
        csv_path = options["csv_file"]
        limit = options["limit"]
        concurrency = options["concurrency"]

        self.stdout.write(f"🚀 Starting optimized async load from {csv_path}")

        # --- Load CSV ---
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {csv_path}"))
            return

        if limit > 0:
            rows = rows[:limit]

        # --- Preload existing keys (IDEMPOTENCY FAST PATH) ---
        existing = await sync_to_async(set)(
            FuelStationModel.objects.values_list(
                "truckstop_name", "address", "city", "state"
            )
        )

        def make_key(r):
            return (
                r["Truckstop Name"].strip(),
                r["Address"].strip(),
                r["City"].strip(),
                r["State"].strip(),
            )

        rows = [r for r in rows if make_key(r) not in existing]

        self.stdout.write(f"📦 Rows after deduplication: {len(rows)}")

        # --- City cache (BIG WIN) ---
        city_cache = {}

        semaphore = asyncio.Semaphore(concurrency)
        station_objects = []
        count = 0

        # --- Async Mapbox call ---
        async def geocode(session, city, state):
            key = f"{city}_{state}"

            if key in city_cache:
                return city_cache[key]

            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{city},{state}.json"

            params = {
                "access_token": settings.MAPBOX_ACCESS_TOKEN,
                "limit": 1,
            }

            try:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status != 200:
                        return None

                    data = await resp.json()
                    features = data.get("features")

                    if not features:
                        return None

                    lon, lat = features[0]["geometry"]["coordinates"]

                    coords = (lat, lon)
                    city_cache[key] = coords
                    return coords

            except Exception:
                return None

        # --- Worker ---
        async def process_row(session, row):
            nonlocal count

            async with semaphore:
                try:
                    name = row["Truckstop Name"].strip()
                    address = row["Address"].strip()
                    city = row["City"].strip()
                    state = row["State"].strip()
                    rack_id = int(row["Rack ID"])
                    price = float(row["Retail Price"])

                    coords = await geocode(session, city, state)

                    if not coords:
                        return

                    # --- jitter ---
                    lat = coords[0] + random.uniform(-0.02, 0.02)
                    lon = coords[1] + random.uniform(-0.02, 0.02)

                    # --- H3 ---
                    try:
                        h3_index = (
                            h3.latlng_to_cell(lat, lon, 7)
                            if hasattr(h3, "latlng_to_cell")
                            else h3.geo_to_h3(lat, lon, 7)
                        )
                    except Exception:
                        h3_index = ""

                    station_objects.append(
                        FuelStationModel(
                            truckstop_name=name,
                            address=address,
                            city=city,
                            state=state,
                            rack_id=rack_id,
                            retail_price=price,
                            latitude=lat,
                            longitude=lon,
                            h3_index=h3_index,
                        )
                    )

                    count += 1

                    # --- Batch insert ---
                    if len(station_objects) >= 1000:
                        await flush()

                    if count % 100 == 0:
                        self.stdout.write(f"Processed {count}")

                except Exception:
                    pass

        # --- Bulk insert ---
        async def flush():
            nonlocal station_objects
            if not station_objects:
                return

            await sync_to_async(FuelStationModel.objects.bulk_create)(
                station_objects,
                ignore_conflicts=True,
            )
            station_objects = []

        # --- Run ---
        async with aiohttp.ClientSession() as session:
            await asyncio.gather(*(process_row(session, r) for r in rows))

        await flush()

        self.stdout.write(
            self.style.SUCCESS(f"✅ Finished. Inserted: {count}")
        )