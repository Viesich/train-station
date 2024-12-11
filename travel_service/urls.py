from rest_framework import routers

from django.urls import path, include

from travel_service.views import (
    StationViewSet,
    RouteViewSet,
    TrainTypeViewSet,
    TrainViewSet,
    CrewViewSet,
    JourneyViewSet,
    OrderViewSet,
)

app_name = "travel_service"

router = routers.DefaultRouter()

router.register("stations", StationViewSet)
router.register("order", OrderViewSet)
router.register("routes", RouteViewSet)
router.register("train-types", TrainTypeViewSet)
router.register("trains", TrainViewSet)
router.register("crews", CrewViewSet)
router.register("journeys", JourneyViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
