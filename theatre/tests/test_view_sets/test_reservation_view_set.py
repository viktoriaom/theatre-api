from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory
from theatre.models import Reservation, Ticket
from theatre.serializers import (
    ReservationListSerializer,
    ReservationSerializer,
)
from theatre.views import ReservationViewSet

from theatre_api import settings
from theatre.tests.helpers import (
    create_and_login_user,
    create_test_performance,
    create_test_reservation,
    create_test_ticket
)

RESERVATION_URL = reverse("theatre:reservations-list")
PAGE_SIZE = settings.REST_FRAMEWORK.get("PAGE_SIZE", 10)


def detail_url(reservation_id):
    return reverse("theatre:reservations-detail",
                   kwargs={"pk": reservation_id})


class UnauthenticatedReservationViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(RESERVATION_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedReservationViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user, self.client = create_and_login_user()
        self.performance = create_test_performance()

    def test_list_own_reservations_only(self):
        own_reservation = create_test_reservation(user=self.user)
        create_test_ticket(reservation=own_reservation,
                           performance=self.performance,
                           row=2,
                           seat=2
                           )

        other_user, _ = create_and_login_user()
        other_reservation = create_test_reservation(user=other_user)
        create_test_ticket(reservation=other_reservation,
                           performance=self.performance)

        res = self.client.get(RESERVATION_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], own_reservation.id)

    def test_list_shows_tickets(self):
        reservation = create_test_reservation(user=self.user)
        create_test_ticket(reservation=reservation,
                           performance=self.performance,
                           row=2,
                           seat=1
                           )
        create_test_ticket(reservation=reservation,
                           performance=self.performance,
                           row=2,
                           seat=2
                           )

        res = self.client.get(RESERVATION_URL)
        self.assertIn("tickets", res.data["results"][0])
        self.assertEqual(len(res.data["results"][0]["tickets"]), 2)

        ticket_data = res.data["results"][0]["tickets"][0]
        self.assertIn("performance", ticket_data)
        self.assertIn("row", ticket_data)
        self.assertIn("seat", ticket_data)

    def test_list_shows_user_email(self):
        reservation = create_test_reservation(user=self.user)
        create_test_ticket(reservation=reservation,
                           performance=self.performance)

        res = self.client.get(RESERVATION_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("user_email", res.data["results"][0])
        self.assertEqual(res.data["results"][0]["user_email"], self.user.email)

    def test_paginated_list_reservations(self):
        reservations_count = PAGE_SIZE + (PAGE_SIZE // 2)
        for _ in range(reservations_count):
            create_test_reservation(user=self.user)
        res = self.client.get(RESERVATION_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertIn("count", res.data)
        self.assertIn("next", res.data)
        self.assertIn("previous", res.data)
        self.assertEqual(len(res.data["results"]), PAGE_SIZE)
        self.assertEqual(res.data["count"], reservations_count)
        self.assertIsNotNone(res.data["next"])
        self.assertIsNone(res.data["previous"])
        res_page_2 = self.client.get(
            RESERVATION_URL, {"limit": PAGE_SIZE, "offset": PAGE_SIZE}
        )
        self.assertEqual(res_page_2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_page_2.data["results"]),
                         reservations_count - PAGE_SIZE)
        self.assertIsNone(res_page_2.data["next"])
        self.assertIsNotNone(res_page_2.data["previous"])

    def test_detail_own_reservation(self):
        reservation = create_test_reservation(user=self.user)
        create_test_ticket(reservation=reservation,
                           performance=self.performance)
        res = self.client.get(detail_url(reservation.id))
        serializer = ReservationListSerializer(reservation)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_detail_shows_tickets(self):
        reservation = create_test_reservation(user=self.user)
        create_test_ticket(reservation=reservation,
                           performance=self.performance,
                           row=2,
                           seat=1
                           )
        create_test_ticket(reservation=reservation,
                           performance=self.performance,
                           row=2,
                           seat=2
                           )

        res = self.client.get(detail_url(reservation.id))
        self.assertIn("tickets", res.data)
        self.assertEqual(len(res.data["tickets"]), 2)

        ticket_data = res.data["tickets"][0]
        self.assertIn("performance", ticket_data)
        self.assertIn("row", ticket_data)
        self.assertIn("seat", ticket_data)

    def test_cannot_retrieve_other_user_reservation(self):
        other_user, _ = create_and_login_user()
        reservation = create_test_reservation(user=other_user)

        url = detail_url(reservation.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_reservation_with_tickets(self):
        payload = {
            "tickets": [
                {
                    "row": 1,
                    "seat": 1,
                    "performance": self.performance.id,
                },
                {
                    "row": 1,
                    "seat": 2,
                    "performance": self.performance.id,
                },
            ]
        }

        res = self.client.post(RESERVATION_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 1)
        self.assertEqual(Ticket.objects.count(), 2)

        reservation = Reservation.objects.first()
        self.assertEqual(reservation.user, self.user)
        self.assertEqual(reservation.tickets.count(), 2)

    def test_create_reservation_without_tickets_forbidden(self):
        payload = {
            "tickets": []
        }
        res = self.client.post(RESERVATION_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_reservation_with_invalid_seats_forbidden(self):
        payload = {
            "tickets": [
                {
                    "row": 999,
                    "seat": 999,
                    "performance": self.performance.id,
                },
                {
                    "row": 456,
                    "seat": 456,
                    "performance": self.performance.id,
                },
            ]
        }

        res = self.client.post(RESERVATION_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_reservation_with_duplicate_seats_forbidden(self):
        payload = {
            "tickets": [
                {
                    "row": 1,
                    "seat": 1,
                    "performance": self.performance.id,
                },
                {
                    "row": 1,
                    "seat": 2,
                    "performance": self.performance.id,
                },
            ]
        }

        res = self.client.post(RESERVATION_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res = self.client.post(RESERVATION_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_atomic_transaction_reservation_creation_fails(self):
        initial_reservations = Reservation.objects.count()
        initial_tickets = Ticket.objects.count()

        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "performance": self.performance.id},
                {"row": 999, "seat": 999, "performance": self.performance.id},
            ]
        }

        res = self.client.post(RESERVATION_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Reservation.objects.count(), initial_reservations)
        self.assertEqual(Ticket.objects.count(), initial_tickets)

    def test_put_reservation_forbidden(self):
        reservation = create_test_reservation(user=self.user)
        payload = {
            "tickets": [
                {
                    "row": 1,
                    "seat": 1,
                    "performance": self.performance.id,
                },
                {
                    "row": 1,
                    "seat": 2,
                    "performance": self.performance.id,
                },
            ]
        }

        res = self.client.put(
            detail_url(reservation.id), payload, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_reservation_forbidden(self):
        reservation = create_test_reservation(user=self.user)
        create_test_ticket(reservation=reservation,
                           performance=self.performance,
                           row=2,
                           seat=2
                           )
        payload = {
            "tickets": [
                {
                    "row": 1,
                    "seat": 1,
                    "performance": self.performance.id,
                },
                {
                    "row": 1,
                    "seat": 2,
                    "performance": self.performance.id,
                },
            ]
        }

        res = self.client.patch(
            detail_url(reservation.id), payload, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_reservation_forbidden(self):
        reservation = create_test_reservation(user=self.user)
        serializer = ReservationListSerializer(reservation)
        res = self.client.get(RESERVATION_URL)
        self.assertIn(serializer.data, res.data["results"])
        res = self.client.delete(detail_url(reservation.id))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_reservation_auto_assigns_user(self):
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "performance": self.performance.id}
            ]
        }

        res = self.client.post(RESERVATION_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        reservation = Reservation.objects.first()
        self.assertEqual(reservation.user, self.user)


class AdminReservationViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user, self.client = create_and_login_user(
            email="admin@example.com", is_staff=True
        )
        self.performance = create_test_performance()

    def test_list_all_reservations_admin(self):
        one_user, _ = create_and_login_user()
        one_reservation = create_test_reservation(user=one_user)
        create_test_ticket(reservation=one_reservation,
                           performance=self.performance,
                           row=2,
                           seat=2
                           )
        two_user, _ = create_and_login_user()
        two_reservation = create_test_reservation(user=two_user)
        create_test_ticket(reservation=two_reservation,
                           performance=self.performance,
                           row=3,
                           seat=3
                           )

        res = self.client.get(RESERVATION_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertEqual(res.data["results"][1]["id"], one_reservation.id)
        self.assertEqual(res.data["results"][0]["id"], two_reservation.id)

    def test_filter_reservations_by_user_id(self):
        one_user, _ = create_and_login_user()
        one_reservation = create_test_reservation(user=one_user)
        create_test_ticket(reservation=one_reservation,
                           performance=self.performance,
                           row=2,
                           seat=2
                           )
        two_user, _ = create_and_login_user()
        two_reservation = create_test_reservation(user=two_user)
        create_test_ticket(reservation=two_reservation,
                           performance=self.performance,
                           row=3,
                           seat=3
                           )

        res = self.client.get(RESERVATION_URL, {"user": f"{one_user.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

        serializer_one = ReservationListSerializer(one_reservation)
        serializer_two = ReservationListSerializer(two_reservation)

        self.assertIn(serializer_one.data, res.data["results"])
        self.assertNotIn(serializer_two.data, res.data["results"])

    def test_filter_reservations_by_performance_id(self):
        user, _ = create_and_login_user()
        one_reservation = create_test_reservation(user=user)
        one_performance = self.performance
        create_test_ticket(reservation=one_reservation,
                           performance=one_performance,
                           row=2,
                           seat=2
                           )
        two_reservation = create_test_reservation(user=user)
        two_performance = create_test_performance()
        create_test_ticket(reservation=two_reservation,
                           performance=two_performance,
                           row=3,
                           seat=3
                           )

        res = self.client.get(
            RESERVATION_URL,
            {"tickets__performance": f"{one_performance.id}"}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

        serializer_one = ReservationListSerializer(one_reservation)
        serializer_two = ReservationListSerializer(two_reservation)

        self.assertIn(serializer_one.data, res.data["results"])
        self.assertNotIn(serializer_two.data, res.data["results"])

    def test_put_reservation_admin_forbidden(self):
        reservation = create_test_reservation()
        payload = {
            "tickets": [
                {
                    "row": 1,
                    "seat": 1,
                    "performance": self.performance.id,
                },
                {
                    "row": 1,
                    "seat": 2,
                    "performance": self.performance.id,
                },
            ]
        }

        res = self.client.put(detail_url(
            reservation.id), payload, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_reservation_admin_forbidden(self):
        reservation = create_test_reservation()
        create_test_ticket(performance=self.performance,
                           reservation=reservation,
                           row=2,
                           seat=2
                           )
        payload = {
            "tickets": [
                {
                    "row": 1,
                    "seat": 1,
                    "performance": self.performance.id,
                },
                {
                    "row": 1,
                    "seat": 2,
                    "performance": self.performance.id,
                },
            ]
        }

        res = self.client.patch(
            detail_url(reservation.id), payload, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_reservation_admin(self):
        reservation = create_test_reservation()
        serializer = ReservationListSerializer(reservation)

        res = self.client.get(RESERVATION_URL)
        self.assertIn(serializer.data, res.data["results"])

        res = self.client.delete(detail_url(reservation.id))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)


class ReservationViewSetSerializerClassTest(TestCase):
    def setUp(self):
        self.viewset = ReservationViewSet()
        self.factory = APIRequestFactory()
        self.request = self.factory.get(RESERVATION_URL)
        self.viewset.request = self.request

    def test_list_action_uses_list_serializer(self):
        self.viewset.action = "list"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, ReservationListSerializer)

    def test_default_action_uses_base_serializer(self):
        self.viewset.action = "create"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, ReservationSerializer)
