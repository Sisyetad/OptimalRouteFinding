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

- Python 3.10+
- Virtual environment (`venv`)

### **Setup**

```bash
# 1. Clone the repository
cd /path/to/OptimalRouteFinding

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Navigate to project directory
cd optimalroute

# 5. Apply migrations
python manage.py migrate

# 6. Load fuel station data (with geocoding)
python manage.py load_fuel_data ../fuel-prices-for-be-assessment.csv --limit 100

# 7. Run the server
python manage.py runserver 0.0.0.0:8000
```

---

## 🔑 **Configuration**

Update `.env` in the root directory:

```ini
ORS_API_KEY=your_openrouteservice_api_key_here
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3  # Or postgres://...
REDIS_URL=redis://localhost:6379/1  # Optional
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

---

## 🧪 **Testing**

```bash
# Run all tests
python manage.py test

# Run specific test modules
python manage.py test domain.services.test_optimization_engine
```

---

## 🛠️ **Advanced Features**

### **Future Enhancements**

- **Dynamic Programming optimization** for better multi-stop strategies
- **Redis caching** for route results (keyed by hash of start-end)
- **PostGIS spatial indexing** for sub-millisecond station queries
- **Rate limiting** and **circuit breakers** for external API calls
- **Celery background tasks** for long routes
- **OpenAPI/Swagger** documentation
- **Docker deployment** with `docker-compose`

---

## 📊 **Performance Characteristics**

| Metric | Value |
|--------|-------|
| **Route Query** | ~500ms (inc. geocoding) |
| **Fuel Station Filtering** | O(n) where n = stations in corridor |
| **Optimization Algorithm** | O(n²) worst case, O(n log n) typical |
| **Database Queries** | 1-2 per request (no N+1) |

---

## 📚 **Dependencies**

- **Django 6.x**
- **Django REST Framework**
- **polyline** (for encoding/decoding routes)
- **haversine** (for distance calculations)
- **geopy** (for geocoding)
- **requests** (for external API calls)
- **environ** (for environment variable management)

---

## 👨‍💻 **Development Notes**

### **Clean Architecture Principles Followed**

✅ **Domain layer is pure Python** (no Django imports)  
✅ **Dependency Inversion**: Infrastructure implements domain interfaces  
✅ **Thin controllers**: Views delegate to use cases  
✅ **Business logic in domain/application layers**  

### **Running Locally**

```bash
# With virtual environment activated
cd optimalroute
python manage.py runserver
```

---

## 📝 **License**

MIT

---

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📧 **Contact**

For questions or support, please open an issue on GitHub.
