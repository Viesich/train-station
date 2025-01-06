from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework import status

from travel_service.models import Station
from travel_service.serializers import (
    StationListSerializer,
    StationDetailSerializer,
    StationSerializer,
)


STATION_URL = reverse("travel_service:station-list")
PYLOAD = {
    "name": "Test_name",
    "latitude": 40,
    "longitude": 50,
}


def detail_url(train_id):
    return reverse("travel_service:station-detail", args=(train_id,))


def sample_station(**params) -> Station:
    defaults = {
        "name": f"Test_name_{Station.objects.count() + 1}",
        "latitude": 40,
        "longitude": 50,
    }
    defaults.update(params)
    return Station.objects.create(**defaults)


class UnauthenticatedTrainApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(STATION_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTrainApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_auth_required(self):
        res = self.client.get(STATION_URL)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_bus_forbidden(self):
        res = self.client.post(STATION_URL, PYLOAD)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAuthenticateTrainApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test", password="testpassword"
        )
        self.user.is_staff = True
        self.user.save()

        self.client.force_authenticate(user=self.user)

    def test_stations_list(self):
        sample_station()
        stations = Station.objects.all()
        serializer = StationListSerializer(stations, many=True)
        with self.assertNumQueries(2):
            res = self.client.get(STATION_URL)
        self.assertEqual(res.data["results"], serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_retrieve_station_detail(self):
        station = sample_station()
        url = detail_url(station.id)
        res = self.client.get(url)
        serializer = StationDetailSerializer(station)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_update_station_with_save(self):
        res = self.client.post(STATION_URL, PYLOAD)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        station = Station.objects.get(id=res.data["id"])
        serializer = StationSerializer(station)
        self.assertEqual(res.data, serializer.data)
        for key in PYLOAD:
            self.assertEqual(PYLOAD[key], getattr(station, key))

        new_pyload = {
            "name": "New Name",
            "latitude": 50,
            "longitude": 50,
        }
        station.name = new_pyload["name"]
        station.latitude = new_pyload["latitude"]
        station.longitude = new_pyload["longitude"]
        station.save()

        station.refresh_from_db()
        for key in new_pyload:
            self.assertEqual(new_pyload[key], getattr(station, key))
