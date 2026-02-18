from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import throttling
from django.conf import settings
from django.core.cache import cache
import hashlib
from interfaces.serializers import RouteRequestSerializer, TripPlanResponseSerializer
from infrastructure.repositories import DjangoFuelRepository
from infrastructure.routing.client import OpenRouteServiceClient
from domain.services.optimization_engine import FuelOptimizationEngine
from application.use_cases.trip_planning import PlanTripUseCase
import environ

env = environ.Env()
environ.Env.read_env(str(settings.BASE_DIR.parent / ".env"))

class PlanTripView(APIView):
    throttle_classes = [throttling.AnonRateThrottle, throttling.UserRateThrottle]

    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        if serializer.is_valid():
            start_loc = serializer.validated_data['start_location']
            end_loc = serializer.validated_data['end_location']

            # Generate Cache Key based on input
            # Normalize to avoid "LA" vs "LA " differences
            cache_key_str = f"trip_plan_{start_loc.strip().lower()}_{end_loc.strip().lower()}"
            cache_key = hashlib.md5(cache_key_str.encode()).hexdigest()
            
            # Check Cache
            cached_response = cache.get(cache_key)
            if cached_response:
                return Response(cached_response, status=status.HTTP_200_OK)
            
            # Composition Root (manual dependency injection)
            # Ideally this would be done via a DI container or Factory
            fuel_repo = DjangoFuelRepository()
            routing_client = OpenRouteServiceClient(api_key=env("ORS_API_KEY"))
            optimizer = FuelOptimizationEngine(vehicle_range=500.0, mpg=10.0)
            
            use_case = PlanTripUseCase(
                routing_service=routing_client,
                fuel_repo=fuel_repo,
                optimizer=optimizer
            )
            
            try:
                result = use_case.execute(start_loc, end_loc)
                response_serializer = TripPlanResponseSerializer(result)
                
                # Store in Cache for 24 hours
                cache.set(cache_key, response_serializer.data, timeout=86400)
                
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
