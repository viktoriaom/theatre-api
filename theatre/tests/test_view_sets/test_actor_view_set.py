from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from theatre.models import Actor
from theatre.tests.helpers import create_and_login_user

ACTOR_URL = reverse("theatre:actors-list")


class ActorViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(ACTOR_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_actors_authenticated(self):
        user, client = create_and_login_user()
        Actor.objects.create(first_name="Tom", last_name="Hanks")

        res = client.get(ACTOR_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

    def test_create_actor_non_admin_forbidden(self):
        user, client = create_and_login_user()
        payload = {"first_name": "Tom", "last_name": "Hanks"}
        res = client.post(ACTOR_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_actor_admin_allowed(self):
        user, client = create_and_login_user(is_staff=True)
        payload = {"first_name": "Tom", "last_name": "Hanks"}

        res = client.post(ACTOR_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Actor.objects.count(), 1)
