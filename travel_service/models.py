from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import UniqueConstraint
from rest_framework.exceptions import ValidationError

from user.models import User

from django.db import models
from django.utils import timezone


class Station(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.name


class Route(models.Model):
    source = models.ForeignKey(
        "Station",
        on_delete=models.CASCADE,
        related_name="source_routes"
    )
    destination = models.ForeignKey(
        "Station",
        on_delete=models.CASCADE,
        related_name="destination_routes"
    )
    distance = models.FloatField()

    class Meta:
        indexes = [
            models.Index(fields=["source", "destination"]),
        ]

    # def __str__(self):
    #     return f"{self.source.name} -> {self.destination.name}"


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Order #{self.id}"


class Ticket(models.Model):
    cargo = models.IntegerField()
    seat = models.IntegerField()
    journey = models.ForeignKey("Journey", on_delete=models.CASCADE, related_name="tickets")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=False, related_name="tickets")

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["cargo", "seat", "journey"],
                name="unique_cargo_seat_journey"
                )
        ]
        ordering = ("cargo", "seat", )

    @staticmethod
    def validate_seat_and_cargo(seat: int, place_in_cargo: int, cargo: int, cargo_num: int, error_to_raise):
        if not (1 <= seat <= place_in_cargo):
            raise error_to_raise(
                {
                    "seat": f"seat must be in range [1, {place_in_cargo}], not {seat}"
                }
            )
        if not (1 <= cargo <= cargo_num):
            raise error_to_raise(
                {
                    "cargo": f"Cargo must be in range [1, {cargo_num}], not {cargo}"
                }
            )

    def clean(self):
        Ticket.validate_seat_and_cargo(
            self.seat,
            self.journey.train.places_in_cargo,
            self.cargo,
            self.journey.train.cargo_num,
            ValueError
        )

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
        **kwargs,
    ):
        self.full_clean()
        return super(Ticket, self).save(
            force_insert, force_update, using, update_fields
        )

    def __str__(self):
        return f"{self.journey} -> {self.cargo}"


class Journey(models.Model):
    route = models.ForeignKey("Route", on_delete=models.CASCADE)
    train = models.ForeignKey("Train", on_delete=models.CASCADE)
    departure_time = models.DateTimeField(default=timezone.now)
    arrival_time = models.DateTimeField(default=timezone.now)
    crews = models.ManyToManyField("Crew", related_name="crews")

    class Meta:
        indexes = [
            models.Index(fields=["departure_time"]),
            models.Index(fields=["arrival_time"]),
        ]

    def __str__(self):
        return f"{self.train} -> {self.route}"


class TrainType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Train(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    cargo_num = models.IntegerField()
    places_in_cargo = models.IntegerField()
    train_type = models.ForeignKey("TrainType", on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Crew(models.Model):
    first_name = models.CharField(max_length=100, db_index=True)
    last_name = models.CharField(max_length=100, db_index=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
