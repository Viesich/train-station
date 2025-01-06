from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework import status

from travel_service.models import Journey, Train, Route, Crew, Station, TrainType, Order
from travel_service.serializers import JourneyListSerializer, JourneyRetrieveSerializer
from travel_service.views import JourneyViewSet


JOURNEY_URL = reverse("travel_service:journey-list")
ORDERS_URL = reverse("travel_service:order-list")
PAYLOAD = {
    "route": None,
    "train": None,
    "departure_time": "2025-01-01 10:00:00",
    "arrival_time": "2025-01-01 15:00:00",
}


def detail_url(journey_id):
    return reverse("travel_service:journey-detail", args=(journey_id,))


class BaseTestSetup(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.station_A = Station.objects.create(name="Kyiv", latitude=50, longitude=50)
        cls.station_B = Station.objects.create(name="Odesa", latitude=60, longitude=50)
        cls.route = Route.objects.create(
            source=cls.station_A, destination=cls.station_B, distance=500
        )

        cls.train_type = TrainType.objects.create(name="Express")
        cls.train = Train.objects.create(
            name="Train A",
            cargo_num=5,
            places_in_cargo=10,
            train_type=cls.train_type,
        )

        cls.crew = Crew.objects.create(first_name="John", last_name="Doe")

        cls.journey = Journey.objects.create(
            route=cls.route,
            train=cls.train,
            departure_time=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            arrival_time=datetime(2025, 1, 1, 15, 0, 0, tzinfo=timezone.utc),
        )
        cls.journey.tickets_available = cls.train.cargo_num * cls.train.places_in_cargo
        cls.journey.save()
        cls.journey.crews.add(cls.crew)

        cls.user = get_user_model().objects.create_user(
            email="testuser@test.com", password="testpassword"
        )


class UnauthenticatedJourneyApiTests(BaseTestSetup):
    def setUp(self):
        self.client = APIClient()

    def test_journey_list_with_tickets_available(self):
        res = self.client.get(JOURNEY_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("tickets_available", res.data["results"][0])
        journey = Journey.objects.first()
        expected_tickets_available = (
            journey.train.cargo_num * journey.train.places_in_cargo - journey.tickets.count()
        )
        self.assertEqual(
            res.data["results"][0]["tickets_available"], expected_tickets_available
        )
        viewset = JourneyViewSet()
        viewset.action = "list"
        with self.assertNumQueries(3):
            queryset = viewset.get_queryset()
            list(queryset)

    def test_retrieve_journey_detail(self):
        url = detail_url(self.journey.id)
        res = self.client.get(url)
        serializer = JourneyRetrieveSerializer(self.journey)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


class AuthenticatedJourneyApiTests(BaseTestSetup):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_list_journeys(self):
        res = self.client.get(JOURNEY_URL)
        journeys = Journey.objects.all()
        serializer = JourneyListSerializer(journeys, many=True)
        self.assertEqual(res.data["results"], serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_retrieve_journey_detail(self):
        url = detail_url(self.journey.id)
        res = self.client.get(url)
        serializer = JourneyRetrieveSerializer(self.journey)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_journey(self):
        PAYLOAD["route"] = self.route.id
        PAYLOAD["train"] = self.train.id
        PAYLOAD["crews"] = [self.crew.id]

        res = self.client.post(JOURNEY_URL, PAYLOAD)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        journey = Journey.objects.get(id=res.data["id"])
        self.assertEqual(res.data["id"], journey.id)
        self.assertEqual(res.data["route"], journey.route.id)
        self.assertEqual(res.data["train"], journey.train.id)
        self.assertEqual(
            res.data["crews"], list(journey.crews.values_list("id", flat=True))
        )
        self.assertEqual(
            res.data["departure_time"],
            journey.departure_time.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        )
        self.assertEqual(
            res.data["arrival_time"],
            journey.arrival_time.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        )


class UnauthenticatedOrderApiTests(BaseTestSetup):
    def setUp(self):
        self.client = APIClient()

    def test_list_orders_unauthenticated(self):
        res = self.client.get(ORDERS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_order_unauthenticated(self):
        res = self.client.post(ORDERS_URL, PAYLOAD)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedOrderApiTests(BaseTestSetup):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_order_with_tickets(self):
        payload = {
            "tickets": [
                {"seat": 1, "cargo": 1, "journey": self.journey.id},
                {"seat": 2, "cargo": 5, "journey": self.journey.id},
            ]
        }
        res = self.client.post(ORDERS_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)

    def test_list_user_orders(self):
        order = Order.objects.create(user=self.user)
        res = self.client.get(ORDERS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], order.id)
