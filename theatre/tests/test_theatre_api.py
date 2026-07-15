from django.contrib.auth import get_user_model
from django.test import TestCase
from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

PLAY_URL = reverse("theatre:plays-list")


class GetTokensTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_tokens(self):
        get_user_model().objects.create_user(
            email="test@example.com", password="testpass123"
        )
        response = self.client.post(
            "/api/user/token/",
            {"email": "test@example.com", "password": "testpass123"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        refresh_token = response.data["refresh"]

        refresh_res = self.client.post(
            "/api/user/token/refresh/", {"refresh": refresh_token}
        )

        self.assertEqual(refresh_res.status_code, 200)
        self.assertIn("access", refresh_res.data)

    def test_list_plays_missing_token(self):
        self.client.credentials()  # Remove token
        res = self.client.get(PLAY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_plays_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalidtoken123")
        res = self.client.get(PLAY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class ThrottlingTheatreApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    @patch("theatre.views.PlayViewSet.permission_classes", [AllowAny])
    def test_throttling_anonymous(self):
        cache.clear()
        for num in range(101):
            res = self.client.get(PLAY_URL)
            if num < 100:
                self.assertNotEqual(res.status_code,
                                    status.HTTP_429_TOO_MANY_REQUESTS)
            else:
                self.assertEqual(res.status_code,
                                 status.HTTP_429_TOO_MANY_REQUESTS)

    def test_throttling_user(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            email="test_user@example.com",
            password="testuser",
        )
        response = self.client.post(
            "/api/user/token/",
            {"email": "test_user@example.com", "password": "testuser"},
        )
        self.token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        for num in range(1001):
            res = self.client.get(PLAY_URL)
            if num < 1000:
                self.assertEqual(res.status_code, status.HTTP_200_OK)
            else:
                self.assertEqual(res.status_code,
                                 status.HTTP_429_TOO_MANY_REQUESTS)
