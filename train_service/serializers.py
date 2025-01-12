from collections import defaultdict

from django.db import transaction

from rest_framework import serializers

from train_service.models import (
    Order,
    Station,
    Route,
    TrainType,
    Train,
    Crew,
    Journey,
    Ticket,
)


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ("id", "name", "latitude", "longitude")


class StationListSerializer(StationSerializer):
    class Meta(StationSerializer.Meta):
        fields = (
            "id",
            "name",
        )


class StationDetailSerializer(StationSerializer):
    class Meta(StationSerializer.Meta):
        fields = ("id", "name", "latitude", "longitude")


class RouteSerializer(serializers.ModelSerializer):
    source = serializers.PrimaryKeyRelatedField(queryset=Station.objects.all())
    destination = serializers.PrimaryKeyRelatedField(queryset=Station.objects.all())

    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class RouteListSerializer(RouteSerializer):
    source = serializers.SlugRelatedField(read_only=True, slug_field="name")
    destination = serializers.SlugRelatedField(read_only=True, slug_field="name")
    distance = serializers.SerializerMethodField()

    @staticmethod
    def get_distance(obj: Route) -> str:
        return f"{obj.distance} km"


class TrainTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainType
        fields = ("id", "name")


class TrainSerializer(serializers.ModelSerializer):
    train_type = serializers.PrimaryKeyRelatedField(queryset=TrainType.objects.all())

    class Meta:
        model = Train
        fields = ("id", "name", "cargo_num", "places_in_cargo", "train_type", "image")


class TrainListSerializer(TrainSerializer):
    train_type = serializers.SlugRelatedField(
        read_only=True,
        slug_field="name",
    )


class TrainImageSerializer(TrainSerializer):
    class Meta:
        model = Train
        fields = ("id", "image")


class CrewSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Crew
        fields = ("id", "full_name")

    @staticmethod
    def get_full_name(obj: Crew) -> str:
        return f"{obj.first_name} {obj.last_name}"


class CrewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name")


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = (
            "id",
            "seat",
            "cargo",
            "journey",
        )

    def validate(self, attrs: dict) -> dict:
        Ticket.validate_seat_and_cargo(
            attrs["seat"],
            attrs["journey"].train.places_in_cargo,
            attrs["cargo"],
            attrs["journey"].train.cargo_num,
            serializers.ValidationError,
        )
        return attrs


class JourneySerializer(serializers.ModelSerializer):

    class Meta:
        model = Journey
        fields = ("id", "route", "train", "crews", "departure_time", "arrival_time")


class JourneyRetrieveSerializer(serializers.ModelSerializer):
    route = serializers.SerializerMethodField()
    train = serializers.PrimaryKeyRelatedField(source="train.name", read_only=True)
    departure_time = serializers.SerializerMethodField()
    arrival_time = serializers.SerializerMethodField()
    crews = serializers.SerializerMethodField()
    free_seats_by_cargo = serializers.SerializerMethodField()

    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "train",
            "departure_time",
            "arrival_time",
            "crews",
            "free_seats_by_cargo",
        )

    @staticmethod
    def get_crews(obj: Journey) -> list:
        return [f"{crew.first_name} {crew.last_name}" for crew in obj.crews.all()]

    @staticmethod
    def get_departure_time(obj: Journey) -> str:
        return f"{obj.departure_time.strftime('%Y-%m-%d %H:%M')}"

    @staticmethod
    def get_arrival_time(obj: Journey) -> str:
        return f"{obj.arrival_time.strftime('%Y-%m-%d %H:%M')}"

    @staticmethod
    def get_route(obj: Journey) -> str:
        return (
            f"{obj.route.source} -> {obj.route.destination} ({obj.route.distance} km)"
        )

    @staticmethod
    def get_free_seats_by_cargo(obj: Journey) -> list:
        total_places_per_cargo = obj.train.places_in_cargo
        total_cargos = obj.train.cargo_num

        taken_seats = obj.tickets.values("cargo", "seat").order_by("cargo", "seat")

        taken_seats_dict = defaultdict(set)
        for ticket in taken_seats:
            taken_seats_dict[ticket["cargo"]].add(ticket["seat"])

        free_seats = []
        for cargo in range(1, total_cargos + 1):
            occupied_seats = taken_seats_dict.get(cargo, set())
            all_seats = set(range(1, total_places_per_cargo + 1))
            available_seats = sorted(all_seats - occupied_seats)

            free_seats.append(
                {"cargo": cargo, "free_seats": ", ".join(map(str, available_seats))}
            )

        return free_seats


class JourneyListSerializer(JourneyRetrieveSerializer):
    tickets_available = serializers.IntegerField()

    class Meta:
        model = Journey
        fields = ("id", "route", "departure_time", "tickets_available")


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_null=False)

    class Meta:
        model = Order
        fields = ("id", "created_at", "user", "tickets")
        read_only_fields = (
            "id",
            "created_at",
            "user",
        )

    def validate(self, attrs: dict) -> dict:
        tickets = attrs.get("tickets")
        if not tickets or len(tickets) == 0:
            raise serializers.ValidationError(
                "The order must contain at least one ticket."
            )
        return attrs

    def create(self, validated_data: dict) -> Order:
        tickets_data = validated_data.pop("tickets")
        user = self.context["request"].user

        if user.is_anonymous:
            raise serializers.ValidationError(
                "User must be logged in to create an order."
            )

        validated_data.pop("user", None)

        with transaction.atomic():
            order = Order.objects.create(user=user, **validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order

    def update(self, instance: Order, validated_data: dict) -> Order:
        instance.user = validated_data.get("user", instance.user)
        instance.save()
        tickets_data = validated_data.get("tickets", None)
        if tickets_data:
            instance.tickets.all().delete()
            for ticket_data in tickets_data:
                Ticket.objects.create(order=instance, **ticket_data)
        return instance


class OrderListSerializer(serializers.ModelSerializer):
    ticket = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "created_at",
            "ticket",
        )
        ordering = ("created_at",)

    @staticmethod
    def get_ticket(obj: Order) -> list:
        tickets = obj.tickets.all()
        return [
            {
                "journey": f"{ticket.journey.route.source.name} -> "
                f"{ticket.journey.route.destination.name} ("
                f"{ticket.journey.train.name})",
                "cargo": ticket.cargo,
                "seat": ticket.seat,
                "departure_time": ticket.journey.departure_time.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "arrival_time": ticket.journey.arrival_time.strftime("%Y-%m-%d %H:%M"),
            }
            for ticket in tickets
        ]
