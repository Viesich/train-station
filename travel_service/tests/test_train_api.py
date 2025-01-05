from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework import status

from travel_service.models import Train, TrainType
from travel_service.serializers import TrainSerializer, TrainTypeSerializer, TrainListSerializer
from travel_service.views import TrainViewSet


TRAIN_URL = reverse("travel_service:train-list")


def detail_url(train_id):
    return reverse("travel_service:train-detail", args=(train_id,))


def sample_train(**params) -> Train:
    train_type = TrainType.objects.create(name="Express")
    defaults = {
        "name": f"Test_name_{Train.objects.count() + 1}",
        "cargo_num": 10,
        "places_in_cargo": 50,
        "train_type": train_type,
    }
    defaults.update(params)
    return Train.objects.create(**defaults)


class UnauthenticatedTrainApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(TRAIN_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTrainApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_auth_required(self):
        res = self.client.get(TRAIN_URL)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_bus_forbidden(self):
        train_type = TrainType.objects.create(name="Express")
        pyload = {
            "name": "Test_name",
            "cargo_num": 10,
            "places_in_cargo": 50,
            "train_type": train_type
        }
        res = self.client.post(TRAIN_URL, pyload)
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

    def test_trains_list(self):
        sample_train()
        res = self.client.get(TRAIN_URL)
        trains = Train.objects.all()
        serializer = TrainListSerializer(trains, many=True)
        self.assertEqual(res.data["results"], serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_trains_by_train_type_id(self):
        train_type2 = TrainType.objects.create(name="Cargo")

        train1 = sample_train()
        train2 = sample_train(train_type=train_type2)

        res = self.client.get(TRAIN_URL, {"train_type": train_type2.id})

        serializer_with_train_type1 = TrainListSerializer(train1)
        serializer_with_train_type2 = TrainListSerializer(train2)
        self.assertNotIn(serializer_with_train_type1.data, res.data["results"])
        self.assertIn(serializer_with_train_type2.data, res.data["results"])

    def test_retrieve_train_detail(self):
        train = sample_train()
        url = detail_url(train.id)
        res = self.client.get(url)
        serializer = TrainListSerializer(train)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_train(self):
        train_type = TrainType.objects.create(name="Express")
        pyload = {
            "name": "Test_name",
            "cargo_num": 10,
            "places_in_cargo": 50,
            "train_type": train_type.id
        }
        res = self.client.post(TRAIN_URL, pyload)
        train = Train.objects.get(id=res.data["id"])
        serializer = TrainSerializer(train)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)
        for key in pyload:
            if key == "train_type":
                self.assertEqual(pyload[key], train.train_type.id)
            else:
                self.assertEqual(pyload[key], getattr(train, key))

    def test_delete_train_not_allowed(self):
        train = sample_train()
        url = detail_url(train.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_params_to_inits_valid_input(self):
        query_string = "1,2,3"
        expected_result = [1, 2, 3]
        result = TrainViewSet._params_to_inits(query_string)
        self.assertEqual(result, expected_result)

    def test_params_to_inits_invalid_input(self):
        query_string = "1,abc,3"
        with self.assertRaises(ValueError):
            TrainViewSet._params_to_inits(query_string)
