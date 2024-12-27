from django.db.models import Count, Prefetch, F
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
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
    OrderSerializer,
    OrderListSerializer,
    JourneyRetrieveSerializer,
    TicketSerializer,
    TrainImageSerializer,
)


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    permission_classes = [IsAdminUser]

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
    permission_classes = [IsAdminUser]

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
    permission_classes = [IsAdminUser]


class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.all()
    permission_classes = [IsAdminUser]

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
        elif self.action in ["create", "partial_update", "update"]:
            return TrainSerializer
        elif self.action == "upload_image":
            return TrainImageSerializer
        return TrainSerializer

    @action(
        methods=[
            "post",
        ],
        detail=True,
        permission_classes=[IsAdminUser],
        url_path="upload-image",
    )
    def upload_image(self, request, pk=None):
        train = self.get_object()
        serializer = self.get_serializer(train, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.all()
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return CrewSerializer
        if self.action in ["create", "partial_update", "update"]:
            return CrewCreateSerializer


class JourneyViewSet(viewsets.ModelViewSet):
    queryset = Journey.objects.all()
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = self.queryset

        if self.action == "list":
            return (
                queryset.select_related()
                .prefetch_related("crews", "tickets")
                .annotate(
                    tickets_available=F("train__cargo_num")
                    * F("train__places_in_cargo")
                    - Count("tickets")
                )
                .order_by("id")
            )
        if self.action == "retrieve":
            return (
                queryset.select_related("route", "train")
                .prefetch_related(
                    "crews",
                    "tickets",
                )
                .order_by("id")
            )

    def get_serializer_class(self):
        if self.action == "list":
            return JourneyListSerializer
        if self.action == "retrieve":
            return JourneyRetrieveSerializer
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
    queryset = Order.objects.prefetch_related(
        Prefetch(
            "tickets",
            queryset=Ticket.objects.select_related(
                "journey__route__source",
                "journey__route__destination",
                "journey__train",
            ),
        )
    )
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        if self.action == "list":
            return queryset.select_related().prefetch_related(
                "tickets",
                "tickets__journey__crews",
                "tickets__journey__train",
                "tickets__journey__route",
            )
        return queryset

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return OrderListSerializer
        if self.action in ["create", "partial_update", "update"]:
            return OrderSerializer
        return OrderListSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
