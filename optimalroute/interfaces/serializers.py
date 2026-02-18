from rest_framework import serializers

class RouteRequestSerializer(serializers.Serializer):
    start_location = serializers.CharField(required=True)
    end_location = serializers.CharField(required=True)

class FuelStationSerializer(serializers.Serializer):
    truckstop_name = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    price_per_gallon = serializers.FloatField()
    gallons_filled = serializers.FloatField()
    cost = serializers.FloatField()
    mile_marker = serializers.FloatField()
    score = serializers.FloatField()

class FuelSummarySerializer(serializers.Serializer):
    total_cost = serializers.FloatField()
    total_gallons = serializers.FloatField()
    total_stops = serializers.IntegerField()

class RouteSerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    duration_minutes = serializers.FloatField()
    polyline = serializers.CharField()

class ProgressionItemSerializer(serializers.Serializer):
    mile = serializers.FloatField()
    total_spent = serializers.FloatField()

class TripPlanResponseSerializer(serializers.Serializer):
    route = RouteSerializer()
    fuel_summary = FuelSummarySerializer()
    stops = FuelStationSerializer(many=True)
    per_mile_progression = ProgressionItemSerializer(many=True)
