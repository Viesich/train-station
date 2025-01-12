from rest_framework.test import APIClient
from rest_framework import status

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase


class CreateUserTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("user:create")

    def test_create_user_success(self):
        payload = {
            "email": "testuser@example.com",
            "password": "testpass123",
        }
        res = self.client.post(self.url, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", res.data)


class ManageUserTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testuser@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("user:manage")

    def test_update_user_success(self):
        payload = {
            "email": "newemail@example.com",
        }
        res = self.client.patch(self.url, payload)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, payload["email"])
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_update_user_with_invalid_password(self):
        payload = {
            "password": "newpassword123",
        }
        res = self.client.patch(self.url, payload)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(payload["password"]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class ManageUserTestUnauthorized(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("user:manage")

    def test_update_user_not_authenticated(self):
        payload = {
            "email": "newemail@example.com",
        }
        res = self.client.patch(self.url, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class ManageUserUpdatePasswordTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testuser@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("user:manage")

    def test_update_password_without_old_password(self):
        payload = {
            "password": "newpassword123",
        }
        res = self.client.patch(self.url, payload)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(payload["password"]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
