from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework import status

from train_service.models import Route, Station
from train_service.serializers import RouteListSerializer


ROUTE_URL = reverse("train_service:route-list")
PAYLOAD = {
    "source": None,
    "destination": None,
    "distance": 500,
}


def detail_url(route_id):
    return reverse("train_service:route-detail", args=(route_id,))


def sample_route(**params):
    city_A = Station.objects.create(name="Kyiv", latitude=50, longitude=50)
    city_B = Station.objects.create(name="Odesa", latitude=60, longitude=50)
    defaults = {"source": city_A, "destination": city_B, "distance": 500}
    defaults.update(params)
    return Route.objects.create(**defaults)


class UnauthenticatedRouteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(ROUTE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedRouteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_auth_required(self):
        res = self.client.get(ROUTE_URL)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_route_forbidden(self):
        pyload = {
            "source": Station.objects.create(name="Kyiv", latitude=50, longitude=50),
            "destination": Station.objects.create(
                name="Odesa", latitude=60, longitude=50
            ),
            "distance": 100,
        }
        res = self.client.post(ROUTE_URL, pyload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAuthenticateRouteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test", password="testpassword"
        )
        self.user.is_staff = True
        self.user.save()
        self.client.force_authenticate(user=self.user)

    def test_list_routes(self):
        sample_route()
        routes = Route.objects.all()
        serializer = RouteListSerializer(routes, many=True)
        with self.assertNumQueries(2):
            res = self.client.get(ROUTE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_route_detail(self):
        route = sample_route()
        url = detail_url(route.id)
        res = self.client.get(url)
        serializer = RouteListSerializer(route)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_route(self):
        city_A = Station.objects.create(name="Kyiv", latitude=50, longitude=50)
        city_B = Station.objects.create(name="Odesa", latitude=60, longitude=50)

        payload = {
            "source": city_A.id,
            "destination": city_B.id,
            "distance": 100,
        }

        res = self.client.post(ROUTE_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        route = Route.objects.get(id=res.data["id"])
        self.assertEqual(route.source.id, city_A.id)
        self.assertEqual(route.destination.id, city_B.id)
        self.assertEqual(route.distance, 100)
