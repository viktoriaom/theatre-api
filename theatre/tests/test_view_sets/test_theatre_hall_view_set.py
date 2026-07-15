from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from theatre.models import TheatreHall
from theatre.tests.helpers import create_and_login_user

THEATRE_HALL_URL = reverse("theatre:theatre_halls-list")


class TheatreHallViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(THEATRE_HALL_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_theatre_halls_authenticated(self):
        user, client = create_and_login_user()
        TheatreHall.objects.create(name="Xenia", rows=10, seats_in_row=20)

        res = client.get(THEATRE_HALL_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

    def test_create_theatre_hall_non_admin_forbidden(self):
        user, client = create_and_login_user()
        payload = {"name": "Xenia",
                   "rows": 10,
                   "seats_in_row": 20
                   }
        res = client.post(THEATRE_HALL_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_theatre_hall_admin_allowed(self):
        user, client = create_and_login_user(is_staff=True)
        payload = {"name": "Xenia",
                   "rows": 10,
                   "seats_in_row": 20
                   }

        res = client.post(THEATRE_HALL_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TheatreHall.objects.count(), 1)
