from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

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
    source = serializers.SerializerMethodField()
    destination = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()

    @staticmethod
    def get_distance(obj):
        return f"{obj.distance} km"

    @staticmethod
    def get_source(obj):
        return obj.source.name

    @staticmethod
    def get_destination(obj):
        return obj.destination.name


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


class CrewCreateSerializer(CrewSerializer):
    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name")


class JourneySerializer(serializers.ModelSerializer):
    class Meta:
        model = Journey
        fields = ("id", "route", "train", "departure_time", "arrival_time", "crew")


class JourneyListSerializer(JourneySerializer):
    route = serializers.SerializerMethodField()
    train = serializers.PrimaryKeyRelatedField(source="train.name", read_only=True)
    departure_time = serializers.SerializerMethodField()
    arrival_time = serializers.SerializerMethodField()
    crew = serializers.SerializerMethodField()

    def get_departure_time(self, obj):
        return f"{obj.departure_time.strftime('%Y-%m-%d %H:%M')}"

    def get_arrival_time(self, obj):
        return f"{obj.arrival_time.strftime('%Y-%m-%d %H:%M')}"

    def get_route(self, obj):
        return f"{obj.route.source} -> {obj.route.destination} ({obj.route.distance} km)"

    def get_crew(self, obj):
        return [f"{crew.first_name} {crew.last_name}" for crew in obj.crew.all()]


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = (
            "id",
            "seat",
            "cargo",
            "journey",
            "order",
        )
        read_only_fields = ["order"]
        validators = [
            UniqueTogetherValidator(
                queryset=Ticket.objects.all(),
                fields=("seat", "cargo", "journey"),
            )
        ]


class TicketListSerializer(TicketSerializer):
    journey = JourneyListSerializer(read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True)

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

        with transaction.atomic():
            order = Order.objects.create(user=user, **validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order


class OrderListSerializer(serializers.ModelSerializer):
    ticket = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ("ticket", )

    def get_ticket(self, obj):
        tickets = obj.tickets.select_related("journey__route", "journey__train").all()
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
