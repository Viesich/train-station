from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework import status

from travel_service.models import Crew
from travel_service.serializers import CrewSerializer, CrewCreateSerializer

CREW_URL = reverse("travel_service:crew-list")


def detail_url(crew_id):
    return reverse("travel_service:crew-detail", args=(crew_id,))


def sample_crew(**params) -> Crew:
    defaults = {
        "first_name": f"First_{Crew.objects.count() + 1}",
        "last_name": f"Last_{Crew.objects.count() + 1}",
    }
    defaults.update(params)
    return Crew.objects.create(**defaults)


class UnauthenticatedCrewApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(CREW_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCrewApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_access_forbidden(self):
        res = self.client.get(CREW_URL)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAuthenticateCrewApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test", password="testpassword"
        )
        self.user.is_staff = True
        self.user.save()

        self.client.force_authenticate(user=self.user)

    def test_list_crew(self):
        sample_crew()
        sample_crew()

        res = self.client.get(CREW_URL)
        crews = Crew.objects.all()
        serializer = CrewSerializer(crews, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_crew_detail(self):
        crew = sample_crew()

        url = detail_url(crew.id)
        res = self.client.get(url)

        serializer = CrewSerializer(crew)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_crew(self):
        payload = {
            "first_name": "John",
            "last_name": "Doe",
        }
        res = self.client.post(CREW_URL, payload)
        crew = Crew.objects.get(id=res.data["id"])
        serializer = CrewSerializer(crew)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)
        for key in payload:
            self.assertEqual(payload[key], getattr(crew, key))

    def test_partial_update_crew(self):
        crew = sample_crew(first_name="OldFirst", last_name="OldLast")
        payload = {"first_name": "NewFirst"}

        url = detail_url(crew.id)
        res = self.client.patch(url, payload)
        crew.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(crew.first_name, payload["first_name"])
        self.assertEqual(crew.last_name, "OldLast")

    def test_full_update_crew(self):
        crew = sample_crew(first_name="OldFirst", last_name="OldLast")
        payload = {"first_name": "NewFirst", "last_name": "NewLast"}

        url = detail_url(crew.id)
        res = self.client.put(url, payload)
        crew.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(crew.first_name, payload["first_name"])
        self.assertEqual(crew.last_name, payload["last_name"])

    def test_create_crew_invalid(self):
        payload = {
            "first_name": "",
            "last_name": "",
        }
        res = self.client.post(CREW_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("first_name", res.data)
        self.assertIn("last_name", res.data)
