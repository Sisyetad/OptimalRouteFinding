"""
Geocoding Logic Explanation:
The source CSV (fuel-prices-for-be-assessment.csv) contains only:
Truckstop ID, Name, Address (often Highway Exits), City, State, Rack ID, Price.

It lacks explicit Latin/Long coordinates.

To solve this, we use a 2-tiered Geocoding strategy:
1. Primary: Nominatim (OpenStreetMap) API to find coordinates for "City, State, USA".
   - We cache city coordinates to minimize API calls (thousands of stations share cities).
   - We add random "jitter" (+/- 0.05 degrees) to separate stations in the same city visually,
     since we don't have exact street addresses for highway exits.
2. Fallback: If geocoding fails, we skip the record.

Note: In a production environment, we would use a paid Geocoding API (Google/Mapbox)
to resolve the exact "Address" field for better precision than just City center + jitter.
"""

import csv
import time
import random
import h3
from django.core.management.base import BaseCommand
from infrastructure.models import FuelStationModel
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

class Command(BaseCommand):
    help = 'Load fuel data from CSV and geocode addresses using City centroids + Jitter'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of rows to process')

    def handle(self, *args, **options):
        csv_path = options['csv_file']
        limit = options['limit']
        
        # Initialize Geocoder
        geolocator = Nominatim(user_agent="optimal_route_app_loader_v1", timeout=10)
        
        # Cache to storing city coordinates: "City, State" -> (lat, lon)
        city_cache = {}
        
        station_objects = []
        count = 0
        
        self.stdout.write(f"Starting load from {csv_path}...")

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    if limit > 0 and count >= limit:
                        break
                    
                    try:
                        name = row['Truckstop Name']
                        city = row['City'].strip()
                        state = row['State'].strip()
                        rack_id = int(row['Rack ID'])
                        price = float(row['Retail Price'])
                        
                        # Construct Query: "City, State, USA"
                        query = f"{city}, {state}, USA"
                        
                        coords = None
                        
                        # Check Cache
                        if query in city_cache:
                            base_coords = city_cache[query]
                            # Add jitter only if we are using city centroid
                            # Approx 3-5 miles jitter to simulate distribution around city
                            lat_jitter = random.uniform(-0.05, 0.05)
                            lon_jitter = random.uniform(-0.05, 0.05)
                            coords = (base_coords[0] + lat_jitter, base_coords[1] + lon_jitter)
                        else:
                            # Fetch from API
                            self.stdout.write(f"Geocoding new city: {query}")
                            try:
                                location = geolocator.geocode(query)
                                if location:
                                    city_cache[query] = (location.latitude, location.longitude)
                                    coords = (location.latitude, location.longitude)
                                    # Sleep to respect Nominatim usage policy (max 1 req/sec)
                                    time.sleep(1.1) 
                                else:
                                    self.stdout.write(self.style.WARNING(f"Could not geocode {query}"))
                                    continue
                            except GeocoderTimedOut:
                                self.stdout.write(self.style.WARNING(f"Timeout geocoding {query}, sleeping..."))
                                time.sleep(2)
                                continue

                        
                        # Calculate H3 Index
                        h3_index = ""
                        if coords:
                            # Resolution 4 ~ 22km edge length
                            try:
                                if hasattr(h3, 'latlng_to_cell'):
                                    h3_index = h3.latlng_to_cell(coords[0], coords[1], 4)
                                else:
                                    h3_index = h3.geo_to_h3(coords[0], coords[1], 4)
                            except Exception:
                                pass

                            station = FuelStationModel(
                                truckstop_name=name,
                                address=row['Address'],
                                city=city,
                                state=state,
                                rack_id=rack_id,
                                retail_price=price,
                                latitude=coords[0],
                                longitude=coords[1],
                                h3_index=h3_index
                            )
                            station_objects.append(station)
                            
                            # Batch insert every 1000 records
                            if len(station_objects) >= 1000:
                                self.stdout.write(f"Batch inserting {len(station_objects)} records...")
                                FuelStationModel.objects.bulk_create(station_objects)
                                station_objects = []  # Reset batch
                                
                            count += 1
                            
                            if count % 50 == 0:
                                self.stdout.write(f"Processed {count} stations...")
                                
                    except (ValueError, KeyError) as e:
                        self.stdout.write(self.style.ERROR(f"Skipping bad row: {row} - {e}"))
                        continue
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Unexpected error: {e}"))
                        # continue

            # Insert remaining records
            if station_objects:
                self.stdout.write(f"Inserting remaining {len(station_objects)} records...")
                FuelStationModel.objects.bulk_create(station_objects)
            
            self.stdout.write(self.style.SUCCESS(f"Successfully finished loading. Total processed: {count}"))
                
        except FileNotFoundError:
             self.stdout.write(self.style.ERROR(f"File not found: {csv_path}"))
