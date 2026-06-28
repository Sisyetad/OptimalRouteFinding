from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import throttling
from django.conf import settings
from interfaces.serializers import RouteRequestSerializer, TripPlanResponseSerializer
from infrastructure.repositories import DjangoFuelRepository
from domain.error.exceptions import (
    RouteError,
    RouteTooLongError,
    LocationNotRoutableError,
    GeocodingError,
)
from domain.services.optimization_engine import FuelOptimizationEngine
from application.use_cases.trip_planning import PlanTripUseCase
import environ

from infrastructure.routing.client import OpenRouteServiceClient
from config.utils.redis_cache_helper import RedisCacheHelper

env = environ.Env()
environ.Env.read_env(str(settings.BASE_DIR.parent / ".env"))

cache_helper = RedisCacheHelper()
class PlanTripView(APIView):
    throttle_classes = [throttling.AnonRateThrottle, throttling.UserRateThrottle]

    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        if serializer.is_valid():
            start_loc = serializer.validated_data['start_location']
            end_loc = serializer.validated_data['end_location']

            # Generate Cache Key based on input
            # Normalize to avoid "LA" vs "LA " differences
            cache_key_str = f"{start_loc.strip().lower()}_{end_loc.strip().lower()}"
            # Check Cache
            cached_response = cache_helper.get("trip_plan", cache_key_str)
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
                cache_helper.set("trip_plan", cache_key_str, response_serializer.data, ttl=86400)
                
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            
            except RouteTooLongError as e:
                return Response(
                    {"error": str(e), "error_type": "route_too_long"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except LocationNotRoutableError as e:
                return Response(
                    {"error": str(e), "error_type": "location_not_routable"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except GeocodingError as e:
                return Response(
                    {"error": str(e), "error_type": "geocoding_failed"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except RouteError as e:
                return Response(
                    {"error": str(e), "error_type": "routing_error"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                return Response(
                    {"error": f"Unexpected error: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
