from django.db.models import Count
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

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
    OrderSerializer,
    OrderListSerializer,
    JourneyRetrieveSerializer,
    TicketSerializer,
)


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()

    def get_queryset(self):
        queryset = self.queryset
        if self.action in ("list", "retrieve"):
            return queryset.select_related()
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return StationListSerializer
        if self.action == "retrieve":
            return StationDetailSerializer
        if self.action in ["create", "partial_update", "update"]:
            return StationSerializer


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    def get_queryset(self):
        queryset = self.queryset
        if self.action in ("list", "retrieve"):
            return queryset.select_related()
        return queryset

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

    @staticmethod
    def _params_to_inits(query_string):
        return [int(str_id) for str_id in query_string.split(",")]

    def get_queryset(self):
        queryset = self.queryset
        train_type = self.request.query_params.get("train_type")

        if train_type:
            train_type = self._params_to_inits(train_type)
            queryset = self.queryset.filter(train_type__id__in=train_type)
        if self.action == "list":
            return queryset.select_related()
        return queryset.distinct()

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

    def get_queryset(self):
        queryset = self.queryset
        if self.action == "list":
            return (
                queryset
                .select_related("route__source", "route__destination")
                .prefetch_related("crews", "tickets")
                .annotate(tickets_taken=Count("tickets"))
            )
        if self.action == "retrieve":
            return queryset.select_related().prefetch_related("crews", "tickets")
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return JourneyListSerializer
        if self.action == "retrieve":
            return JourneyRetrieveSerializer
        if self.action in ["update", "partial_update"]:
            return JourneySerializer
        return JourneySerializer


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()

    def get_queryset(self):
        queryset = self.queryset
        if self.action == "list":
            return queryset.select_related()
        return queryset

    serializer_class = TicketSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()

    def get_queryset(self):
        queryset = self.queryset
        if self.action == "list":
            return queryset.select_related()
        return queryset

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return OrderListSerializer
        if self.action in ["create", "partial_update", "update"]:
            return OrderSerializer
        return OrderListSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
