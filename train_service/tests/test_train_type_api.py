from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from train_service.models import TrainType
from train_service.serializers import TrainTypeSerializer


TRAIN_TYPE_URL = reverse("train_service:traintype-list")


def detail_url(train_type_id):
    return reverse("train_service:traintype-detail", args=(train_type_id,))


class UnauthenticatedTrainTypeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(TRAIN_TYPE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTrainTypeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_auth_required(self):
        res = self.client.get(TRAIN_TYPE_URL)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_train_type_forbidden(self):
        pyload = {"name": "Kyiv"}
        res = self.client.post(TRAIN_TYPE_URL, pyload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAuthenticateTrainTypeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test", password="testpassword"
        )
        self.user.is_staff = True
        self.user.save()
        self.client.force_authenticate(user=self.user)

    def test_list_train_types(self):
        TrainType.objects.create(name="Express")
        train_types = TrainType.objects.all()
        serializer = TrainTypeSerializer(train_types, many=True)
        with self.assertNumQueries(2):
            res = self.client.get(TRAIN_TYPE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_train_type_detail(self):
        train_type = TrainType.objects.create(name="Express")
        url = detail_url(train_type.id)
        res = self.client.get(url)
        serializer = TrainTypeSerializer(train_type)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_train_type(self):

        payload = {"name": "Kyiv"}

        res = self.client.post(TRAIN_TYPE_URL, payload, format="json")
        train_type = TrainType.objects.get(id=res.data["id"])
        self.assertEqual(train_type.name, "Kyiv")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
