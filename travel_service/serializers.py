from collections import defaultdict

from django.db import transaction
from rest_framework import serializers

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


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ("name", "latitude", "longitude")


class StationListSerializer(StationSerializer):
    class Meta(StationSerializer.Meta):
        fields = ("id", "name", )


class StationDetailSerializer(StationSerializer):
    class Meta(StationSerializer.Meta):
        fields = ("id", "name", "latitude", "longitude")


class RouteSerializer(serializers.ModelSerializer):
    source = serializers.PrimaryKeyRelatedField(
        queryset=Station.objects.all()
    )
    destination = serializers.PrimaryKeyRelatedField(
        queryset=Station.objects.all()
    )

    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class RouteListSerializer(RouteSerializer):
    source = serializers.SlugRelatedField(read_only=True, slug_field="name")
    destination = serializers.SlugRelatedField(read_only=True, slug_field="name")
    distance = serializers.SerializerMethodField()

    @staticmethod
    def get_distance(obj):
        return f"{obj.distance} km"


class TrainTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainType
        fields = ("id", "name")


class TrainSerializer(serializers.ModelSerializer):
    train_type = serializers.PrimaryKeyRelatedField(
        queryset=TrainType.objects.all()
    )

    class Meta:
        model = Train
        fields = ("id", "name", "cargo_num", "places_in_cargo", "train_type")


class TrainListSerializer(TrainSerializer):
    train_type = serializers.PrimaryKeyRelatedField(source="train_type.name", read_only=True)


class CrewSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Crew
        fields = ("id", "full_name")

    @staticmethod
    def get_full_name(obj):
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

    def validate(self, attrs):
        Ticket.validate_seat_and_cargo(
            attrs["seat"],
            attrs["journey"].train.places_in_cargo,
            attrs["cargo"],
            attrs["journey"].train.cargo_num,
            serializers.ValidationError
        )
        return attrs
#
#
# class TicketListSerializer(TicketSerializer):
#     journey = JourneyListSerializer(read_only=True)


class JourneySerializer(serializers.ModelSerializer):

    class Meta:
        model = Journey
        fields = ("route", "train", "crews", "departure_time", "arrival_time")


class JourneyRetrieveSerializer(serializers.ModelSerializer):
    route = serializers.SerializerMethodField()
    train = serializers.PrimaryKeyRelatedField(source="train.name", read_only=True)
    departure_time = serializers.SerializerMethodField()
    arrival_time = serializers.SerializerMethodField()
    crews = serializers.SerializerMethodField()
    taken_seats = serializers.SerializerMethodField()

    class Meta:
        model = Journey
        fields = ("id", "route", "train", "departure_time", "arrival_time", "crews", "taken_seats")

    def get_crews(self, obj):
        return [f"{crew.first_name} {crew.last_name}" for crew in obj.crews.all()]
    def get_departure_time(self, obj):
        return f"{obj.departure_time.strftime('%Y-%m-%d %H:%M')}"

    def get_arrival_time(self, obj):
        return f"{obj.arrival_time.strftime('%Y-%m-%d %H:%M')}"

    def get_route(self, obj):
        return f"{obj.route.source} -> {obj.route.destination} ({obj.route.distance} km)"

    def get_taken_seats(self, obj):
        tickets = obj.tickets.all()
        grouped_seats = defaultdict(list)

        for ticket in tickets:
            grouped_seats[ticket.cargo].append(ticket.seat)

        return [
            {
                "cargo": cargo,
                "seat": ", ".join(map(str, sorted(seats)))
            }
            for cargo, seats in grouped_seats.items()
        ]


class JourneyListSerializer(JourneyRetrieveSerializer):
    tickets_taken = serializers.IntegerField(read_only=True)

    class Meta:
        model = Journey
        fields = ("id", "route", "departure_time", "tickets_taken")


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_null=False)

    class Meta:
        model = Order
        fields = ("id", "created_at", "user", "tickets")
        read_only_fields = ("id", "created_at", "user",)

    def validate(self, attrs):
        tickets = attrs.get("tickets")
        if not tickets or len(tickets) == 0:
            raise serializers.ValidationError("The order must contain at least one ticket.")
        return attrs

    def create(self, validated_data):
        tickets_data = validated_data.pop("tickets")
        user = self.context["request"].user

        if user.is_anonymous:
            raise serializers.ValidationError("User must be logged in to create an order.")

        validated_data.pop("user", None)

        with transaction.atomic():
            order = Order.objects.create(user=user, **validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order


class OrderListSerializer(serializers.ModelSerializer):
    ticket = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ("ticket",)
        ordering = ("created_at", )

    def get_ticket(self, obj):
        tickets = obj.tickets.all()
        return [
            {
                "journey": f"{ticket.journey.route.source.name} -> "
                           f"{ticket.journey.route.destination.name} ("
                           f"{ticket.journey.train.name})",
                "cargo": ticket.cargo,
                "seat": ticket.seat,
                "departure_time": ticket.journey.departure_time.strftime("%Y-%m-%d %H:%M"),
                "arrival_time": ticket.journey.arrival_time.strftime("%Y-%m-%d %H:%M"),
            }
            for ticket in tickets
        ]
