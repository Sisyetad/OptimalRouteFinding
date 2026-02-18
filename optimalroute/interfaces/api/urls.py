from django.urls import path
from interfaces.api.views import PlanTripView

urlpatterns = [
    path('plan-trip/', PlanTripView.as_view(), name='plan-trip'),
]
