from django.test import TestCase

from theatre.serializers import TicketSerializer
from theatre.tests.helpers import (
    create_test_performance,
    create_test_theatre_hall,
    create_test_reservation,
    create_and_login_user,
)


class TicketSerializerValidationTests(TestCase):

    def setUp(self):
        self.user, _ = create_and_login_user()
        self.theatre_hall = create_test_theatre_hall(rows=10, seats_in_row=10)
        self.performance = create_test_performance(
            theatre_hall=self.theatre_hall
        )
        self.reservation = create_test_reservation(user=self.user)

    def test_valid_ticket_data(self):
        data = {
            "row": 1,
            "seat": 1,
            "performance": self.performance.id,
        }

        serializer = TicketSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_row_exceeds_hall_capacity(self):
        data = {
            "row": 11,  # Hall has only 10 rows
            "seat": 1,
            "performance": self.performance.id,
        }

        serializer = TicketSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("row", str(serializer.errors).lower())

    def test_seat_exceeds_row_capacity(self):
        data = {
            "row": 1,
            "seat": 11,  # Row has only 10 seats
            "performance": self.performance.id,
        }

        serializer = TicketSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("seat", str(serializer.errors).lower())

    def test_zero_row(self):
        data = {
            "row": 0,
            "seat": 1,
            "performance": self.performance.id,
        }

        serializer = TicketSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_zero_seat(self):
        data = {
            "row": 1,
            "seat": 0,
            "performance": self.performance.id,
        }

        serializer = TicketSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_negative_row(self):
        data = {
            "row": -1,
            "seat": 1,
            "performance": self.performance.id,
        }

        serializer = TicketSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_negative_seat(self):
        data = {
            "row": 1,
            "seat": -1,
            "performance": self.performance.id,
        }

        serializer = TicketSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_edge_case_max_row(self):
        data = {
            "row": 10,  # Max row in hall
            "seat": 1,
            "performance": self.performance.id,
        }

        serializer = TicketSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_edge_case_max_seat(self):
        data = {
            "row": 1,
            "seat": 10,  # Max seat in row
            "performance": self.performance.id,
        }

        serializer = TicketSerializer(data=data)
        self.assertTrue(serializer.is_valid())
