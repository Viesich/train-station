from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from travel_service.models import (
    Order,
    Station,
    Route,
    TrainType,
    Train,
    Crew,
    Journey,
    Ticket,
)
from travel_service.serializers import (
    StationSerializer,
    StationListSerializer,
    StationDetailSerializer,
    RouteSerializer,
    TrainTypeSerializer,
    TrainSerializer,
    TrainListSerializer,
    RouteListSerializer,
    CrewSerializer,
    CrewCreateSerializer,
    JourneySerializer,
    JourneyListSerializer,
    TicketListSerializer,
    OrderSerializer,
    OrderListSerializer,
)


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()

    def get_queryset(self):
        return Station.objects.order_by("name")

    def get_serializer_class(self):
        if self.action == "list":
            return StationListSerializer
        if self.action == "retrieve":
            return StationDetailSerializer
        if self.action in ["create", "partial_update", "update"]:
            return StationSerializer


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return RouteListSerializer
        if self.action in ["create", "partial_update", "update"]:
            return RouteSerializer


class TrainTypeViewSet(viewsets.ModelViewSet):
    queryset = TrainType.objects.all()
    serializer_class = TrainTypeSerializer


class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.all()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return TrainListSerializer
        if self.action in ["create", "partial_update", "update"]:
            return TrainSerializer


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.all()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return CrewSerializer
        if self.action in ["create", "partial_update", "update"]:
            return CrewCreateSerializer


class JourneyViewSet(viewsets.ModelViewSet):
    queryset = Journey.objects.all()

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return JourneyListSerializer
        return JourneySerializer


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketListSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related(
        "tickets__journey__route", "tickets__journey__train"
    )
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return OrderListSerializer
        if self.action in ["create", "partial_update", "update"]:
            return OrderSerializer
        return OrderListSerializer
