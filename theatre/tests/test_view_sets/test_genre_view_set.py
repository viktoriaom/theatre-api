from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from theatre.models import Genre
from theatre.tests.helpers import create_and_login_user

GENRE_URL = reverse("theatre:genres-list")


class GenreViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(GENRE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_genres_authenticated(self):
        user, client = create_and_login_user()
        Genre.objects.create(name="musical")

        res = client.get(GENRE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

    def test_create_genre_non_admin_forbidden(self):
        user, client = create_and_login_user()
        payload = {"name": "musical"}
        res = client.post(GENRE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_genre_admin_allowed(self):
        user, client = create_and_login_user(is_staff=True)
        payload = {"name": "musical"}

        res = client.post(GENRE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Genre.objects.count(), 1)
