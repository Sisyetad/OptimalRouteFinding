# Optimal Route Finding - Production-Grade REST API

**A Django + DRF system following Clean Architecture principles for optimal fuel route planning.**

---

## 🎯 **System Overview**

This API accepts a start and end location in the USA and returns:
- **Full route map data** (polyline, distance, duration)
- **Optimal fuel stops** (cost-efficient)
- **Per-mile fuel spending progression**
- **Total fuel cost & usage summary**
- **Stop ranking scores**

---

## 🏗️ **Architecture (Clean Architecture)**

```
optimalroute/
│
├── domain/                # ✅ Enterprise business rules (Pure Python, no Django dependency)
│   ├── entities/          # Core domain objects (Route, FuelStation, FuelStopDecision)
│   ├── repositories/      # Repository interfaces
│   └── services/          # Domain services (routing interface, optimization engine)
│
├── application/           # ✅ Use cases
│   └── use_cases/         # PlanTripUseCase (orchestrates routing + optimization)
│
├── infrastructure/        # ✅ External concerns
│   ├── models.py          # Django ORM models
│   ├── repositories.py    # Django implementations of domain repository interfaces
│   ├── routing/           # OpenRouteService client
│   └── management/        # Database seeding commands
│
├── interfaces/            # ✅ API layer (thin controllers)
│   ├── serializers.py     # DRF serializers
│   └── api/
│       ├── views.py       # PlanTripView (APIView)
│       └── urls.py
│
└── config/                # ✅ Django settings & URL routing
```

---

## ⚙️ **Key Features**

###  **1. Intelligent Fuel Stop Optimization**

Uses a **Dijkstra Shortest Path Algorithm**:
- Models the route as a **Directed Acyclic Graph (DAG)** of fuel stations.
- Finds the **globally optimal sequence of stops** to minimize total fuel cost.
- **Minimizes overall trip cost**, not just locally greedy decisions.
- **Constraints**: Vehicle range (500 miles), fuel efficiency (10 MPG).
- **Considers**: Fuel needed to reach next stop vs price difference.

###  **2. Minimal External API Calls**

- **Single routing API call** per start-end pair
- Caching-ready (using Django's cache framework)
- Geocoding + Route fetching combined

###  **3. Scalability & Performance**

- **Bounding box + spatial filtering** for fuel station retrieval
- **Bulk database queries** (no N+1 issues)
- **O(n log n)** station selection complexity
- SQLite for local dev; PostgreSQL + PostGIS ready for production

---

## 📦 **Installation**

### **Prerequisites**

- Python 3.12+
- Virtual environment (`venv`)

### **Setup**

```bash
# 1. Clone the repository
cd /path/to/OptimalRouteFinding/optimalroute

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependenciesADMIN_EMAIL
pip install -r requirements.txt

# 4. Copy .env.example to .env and set your enviroment variables
cp .env.example .env

nano .env

# 4. Navigate to project directory
docker build -t sisyetad/optimalroute:latest .

docker compose up -d
# 5. Apply migrations
docker exec -it django_app python manage.py migrate

# 6. Load fuel station data (with geocoding)
docker exec -it django_app python manage.py load_fuel_data ../fuel-prices-for-be-assessment.csv --limit 100

# 7. Running in the following host
http://127.0.0.0:8000/api/v1/plan-trip
```

## 🔑 **Configuration**

Update `.env` in the root directory:

```ini
ORS_API_KEY=your_openrouteservice_api_key_here
MAPBOX_ACCESS_TOKEN=your_mapbox_api_token
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_NAME=optimalroute
DATABASE_USER=optimalroute
DATABASE_PASSWORD=password123
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_URL= # Or postgres://...
REDIS_URL=redis://localhost:6379/1  # Optional
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@gmail.com
ADMIN_PASSWORD=123
```

---

## 🚀 **Usage**

### **Endpoint**

```
POST /api/plan-trip/
```

### **Request Body**

```json
{
  "start_location": "Los Angeles, CA",
  "end_location": "New York, NY"
}
```

Or use coordinates:

```json
{
  "start_location": "34.0522, -118.2437",
  "end_location": "40.7128, -74.0060"
}
```

```json
  {
    "start_location": "32.7767, -96.7970",
    "end_location": "29.7604, -95.3698"
  }
```

```json
  {
    "start_location": "123 Main St, Dallas, TX 75201",
    "end_location": "456 Oak St, Houston, TX 77002"
  }
```

### **Response**

```json
{
  "route": {
    "distance_miles": 2794.52,
    "duration_minutes": 2508,
    "polyline": "encoded_polyline_string..."
  },
  "fuel_summary": {
    "total_cost": 823.45,
    "total_gallons": 279.45,
    "total_stops": 6
  },
  "stops": [
    {
      "truckstop_name": "PILOT TRAVEL CENTER #1243",
      "city": "Gila Bend",
      "state": "AZ",
      "price_per_gallon": 3.00,
      "gallons_filled": 50.0,
      "cost": 150.00,
      "mile_marker": 472.3,
      "score": 0.92
    }
  ],
  "per_mile_progression": [
    { "mile": 1, "total_spent": 0.0 },
    { "mile": 472, "total_spent": 0.0 },
    { "mile": 473, "total_spent": 150.00 },
    ...
  ]
}
```
