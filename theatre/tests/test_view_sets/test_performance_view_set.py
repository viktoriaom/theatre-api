from django.core.cache import cache
from django.db.models import F
from django.db.models.aggregates import Count
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory
from theatre.models import Performance, Ticket, Reservation
from theatre.serializers import (
    PerformanceListSerializer,
    PerformanceDetailSerializer,
    PerformanceSerializer,
)
from theatre.views import PerformanceViewSet

from theatre_api import settings
from theatre.tests.helpers import (
    create_and_login_user,
    create_test_play,
    create_test_theatre_hall,
    create_test_performance
)

PERFORMANCE_URL = reverse("theatre:performances-list")
PAGE_SIZE = settings.REST_FRAMEWORK.get("PAGE_SIZE", 10)


def detail_url(performance_id):
    return reverse("theatre:performances-detail",
                   kwargs={"pk": performance_id}
                   )


class UnauthenticatedPerformanceViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(PERFORMANCE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedPerformanceViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user, self.client = create_and_login_user()

    def test_list_performances(self):
        create_test_performance()
        create_test_performance()
        res = self.client.get(PERFORMANCE_URL)
        performances = Performance.objects.annotate(
            tickets_available=(
                F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                - Count("tickets")
            )
        ).order_by("id")
        serializer = PerformanceListSerializer(performances, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_correct_tickets_available_list_performances(self):
        performance = create_test_performance()
        reservation = Reservation.objects.create(
            user=self.user,
            created_at=now()
        )
        for num in range(1, 5):
            Ticket.objects.create(
                reservation=reservation,
                performance=performance,
                row=num,
                seat=num,
            )
        count = (performance.theatre_hall.capacity
                 - Ticket.objects.all().count())
        res = self.client.get(PERFORMANCE_URL)
        performances = Performance.objects.annotate(
            tickets_available=(
                    F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                    - Count("tickets")
            )
        ).order_by("id")
        serializer = PerformanceListSerializer(performances, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)
        self.assertEqual(res.data["results"][0]["tickets_available"], count)

    def test_paginated_list_performances(self):
        performances_count = PAGE_SIZE + (PAGE_SIZE // 2)
        for _ in range(performances_count):
            create_test_performance()
        res = self.client.get(PERFORMANCE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertIn("count", res.data)
        self.assertIn("next", res.data)
        self.assertIn("previous", res.data)
        self.assertEqual(len(res.data["results"]), PAGE_SIZE)
        self.assertEqual(res.data["count"], performances_count)
        self.assertIsNotNone(res.data["next"])
        self.assertIsNone(res.data["previous"])
        res_page_2 = self.client.get(
            PERFORMANCE_URL, {"limit": PAGE_SIZE, "offset": PAGE_SIZE}
        )
        self.assertEqual(res_page_2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_page_2.data["results"]),
                         performances_count - PAGE_SIZE)
        self.assertIsNone(res_page_2.data["next"])
        self.assertIsNotNone(res_page_2.data["previous"])

    def test_filter_performances_by_play_id(self):
        play_one = create_test_play()
        play_two = create_test_play()
        create_test_performance(play=play_one)
        create_test_performance(play=play_two)

        performances_one = Performance.objects.annotate(
            tickets_available=(
                    F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                    - Count("tickets")
            )
        ).filter(play=play_one)

        performances_two = Performance.objects.annotate(
            tickets_available=(
                    F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                    - Count("tickets")
            )
        ).filter(play=play_two)

        res = self.client.get(PERFORMANCE_URL, {"play": f"{play_one.id}"})
        serializer_one = PerformanceListSerializer(performances_one, many=True)
        serializer_two = PerformanceListSerializer(performances_two, many=True)

        self.assertEqual(serializer_one.data, res.data["results"])
        self.assertNotEqual(serializer_two.data, res.data["results"])

    def test_filter_performances_by_date(self):
        create_test_performance(show_time="2030-12-31")
        create_test_performance(show_time="2025-12-31")

        performances_one = Performance.objects.annotate(
            tickets_available=(
                    F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                    - Count("tickets")
            )
        ).filter(show_time="2030-12-31")

        performances_two = Performance.objects.annotate(
            tickets_available=(
                    F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                    - Count("tickets")
            )
        ).filter(show_time="2025-12-31")

        res = self.client.get(PERFORMANCE_URL, {"date": "2030-12-31"})
        serializer_one = PerformanceListSerializer(performances_one, many=True)
        serializer_two = PerformanceListSerializer(performances_two, many=True)

        self.assertEqual(serializer_one.data, res.data["results"])
        self.assertNotEqual(serializer_two.data, res.data["results"])

    def test_detail_performance(self):
        performance = create_test_performance()
        res = self.client.get(detail_url(performance.id))

        performance = (
            Performance.objects
            .select_related("play", "theatre_hall")
            .annotate(
                tickets_available=(
                        F("theatre_hall__rows")
                        * F("theatre_hall__seats_in_row")
                        - Count("tickets")
                )
            ).get(id=performance.id)

        )

        serializer = PerformanceDetailSerializer(performance)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_test_performance_not_admin_forbidden(self):
        play = create_test_play()
        theatre_hall = create_test_theatre_hall()
        payload = {
            "play": play.id,
            "theatre_hall": theatre_hall.id,
            "show_time": now(),
        }
        res = self.client.post(PERFORMANCE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_performance_not_admin_forbidden(self):
        performance = create_test_performance()
        play = create_test_play()
        theatre_hall = create_test_theatre_hall()
        payload = {
            "play": play.id,
            "theatre_hall": theatre_hall.id,
            "show_time": now(),
        }
        res = self.client.put(detail_url(performance.id), payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_performance_not_admin_forbidden(self):
        performance = create_test_performance()
        payload = {
            "show_time": now()
        }
        res = self.client.patch(detail_url(performance.id), payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_performance_not_admin_forbidden(self):
        performance = create_test_performance()
        res = self.client.delete(detail_url(performance.id))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminPerformanceViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user, self.client = create_and_login_user(
            email="admin@example.com", is_staff=True
        )

    def test_create_test_performance_admin(self):
        play = create_test_play()
        theatre_hall = create_test_theatre_hall()
        payload = {
            "play": play.id,
            "theatre_hall": theatre_hall.id,
            "show_time": now(),
        }
        res = self.client.post(PERFORMANCE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        performance = Performance.objects.get(show_time=payload["show_time"])
        self.assertEqual(performance.play, play)
        self.assertEqual(performance.show_time, payload["show_time"])
        self.assertEqual(performance.theatre_hall, theatre_hall)

    def test_create_invalid_performance_admin(self):
        play = create_test_play()
        theatre_hall = create_test_theatre_hall()
        payload_with_no_play = {
            "play": "",
            "theatre_hall": theatre_hall.id,
            "show_time": now(),
        }
        payload_with_no_theatre_hall = {
            "play": play.id,
            "theatre_hall": "",
            "show_time": now(),
        }
        payload_with_no_show_time = {
            "play": play.id,
            "theatre_hall": theatre_hall.id,
            "show_time": "",
        }
        res = self.client.post(PERFORMANCE_URL, payload_with_no_play)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = self.client.post(PERFORMANCE_URL, payload_with_no_theatre_hall)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = self.client.post(PERFORMANCE_URL, payload_with_no_show_time)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        payload_with_wrong_play = {
            "play": 1234,
            "theatre_hall": theatre_hall.id,
            "show_time": now(),
        }
        payload_with_wrong_theatre_hall = {
            "play": play.id,
            "theatre_hall": 1234,
            "show_time": now(),
        }
        payload_with_wrong_show_time = {
            "play": play.id,
            "theatre_hall": theatre_hall.id,
            "show_time": 1234,
        }
        res = self.client.post(PERFORMANCE_URL, payload_with_wrong_play)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = self.client.post(PERFORMANCE_URL,
                               payload_with_wrong_theatre_hall)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = self.client.post(PERFORMANCE_URL, payload_with_wrong_show_time)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_performance_admin(self):
        play = create_test_play()
        theatre_hall = create_test_theatre_hall()
        payload = {
            "play": play.id,
            "theatre_hall": theatre_hall.id,
            "show_time": now(),
        }
        performance = create_test_performance()
        res = self.client.put(detail_url(performance.id), payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        performance.refresh_from_db()
        self.assertEqual(performance.play, play)
        self.assertEqual(performance.show_time, payload["show_time"])
        self.assertEqual(performance.theatre_hall, theatre_hall)

    def test_patch_performance_admin(self):
        performance = create_test_performance()
        payload = {
            "show_time": now(),
        }
        res = self.client.patch(detail_url(performance.id), payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        performance.refresh_from_db()
        self.assertEqual(performance.show_time, payload["show_time"])

    def test_delete_performance_admin(self):
        performance = create_test_performance()
        res = self.client.get(PERFORMANCE_URL)
        performances = Performance.objects.annotate(
            tickets_available=(
                    F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                    - Count("tickets")
            )
        ).order_by("id")
        serializer = PerformanceListSerializer(performances, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

        performance_to_delete_url = detail_url(performance.id)
        res = self.client.delete(performance_to_delete_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)


class PerformanceViewSetSerializerClassTest(TestCase):
    def setUp(self):
        self.viewset = PerformanceViewSet()
        self.factory = APIRequestFactory()
        self.request = self.factory.get(PERFORMANCE_URL)
        self.viewset.request = self.request

    def test_list_action_uses_list_serializer(self):
        self.viewset.action = "list"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, PerformanceListSerializer)

    def test_retrieve_action_uses_detail_serializer(self):
        self.viewset.action = "retrieve"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, PerformanceDetailSerializer)

    def test_default_action_uses_base_serializer(self):
        self.viewset.action = "create"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, PerformanceSerializer)
