from uuid import uuid4

from django.utils.timezone import now
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from theatre.models import (
    Play,
    TheatreHall,
    Performance,
    Reservation,
    Ticket,
    Review
)


def create_and_login_user(**params):
    defaults = {
        "email": f"user_{uuid4().hex[:8]}@example.com",
        "password": "testpass123",
        "is_staff": False,
    }
    defaults.update(params)
    client = APIClient()
    user = get_user_model().objects.create_user(**defaults)
    response = client.post(
        "/api/user/token/",
        {"email": defaults["email"], "password": defaults["password"]},
    )
    token = response.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return user, client


def create_test_play(**params) -> Play:
    defaults = {"title": f"Play {uuid4().hex[:6]}",
                "description": "Test description"}
    defaults.update(params)
    return Play.objects.create(**defaults)


def create_test_theatre_hall(**params) -> TheatreHall:
    defaults = {"name": f"Theatre Hall {uuid4().hex[:4]}",
                "rows": 10,
                "seats_in_row": 20
                }
    defaults.update(params)
    return TheatreHall.objects.create(**defaults)


def create_test_performance(**params) -> Performance:
    if "play" not in params:
        params["play"] = create_test_play()

    if "theatre_hall" not in params:
        params["theatre_hall"] = create_test_theatre_hall()

    defaults = {
        "show_time": now(),
    }
    defaults.update(params)
    return Performance.objects.create(**defaults)


def create_test_reservation(**params) -> Reservation:
    if "user" not in params:
        user, client = create_and_login_user(**params)
        params["user"] = user

    defaults = {"created_at": now()}

    defaults.update(params)
    return Reservation.objects.create(**defaults)


def create_test_ticket(**params):
    if "performance" not in params:
        params["performance"] = create_test_performance()
    if "reservation" not in params:
        user, _ = create_and_login_user()
        params["reservation"] = create_test_reservation(user=user)

    defaults = {
        "row": 1,
        "seat": 1,
    }
    defaults.update(params)
    return Ticket.objects.create(**defaults)


def create_test_review(**params) -> Review:
    if "user" not in params:
        user, client = create_and_login_user(**params)
        params["user"] = user

    if "play" not in params:
        params["play"] = create_test_play()

    defaults = {
        "rating": 5,
        "comment": "Test review comment",
    }
    defaults.update(params)
    return Review.objects.create(**defaults)
