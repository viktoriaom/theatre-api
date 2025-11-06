import math
from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.exceptions import ValidationError

from theatre.models import (
    Actor,
    Genre,
    Play,
    Review,
    TheatreHall,
    Performance,
    Reservation,
    Ticket,
)


class ModelsTests(TestCase):

    def create_user(self):
        user = get_user_model().objects.create_user(
            email="<EMAIL>", password="<PASSWORD>"
        )
        return user

    def create_play(self):
        play = Play.objects.create(
            title="Test_title",
            description="Test_description",
        )
        return play

    def create_theatre_hall(self):
        theatre_hall = TheatreHall.objects.create(
            name="Test_theatre_hall",
            rows=10,
            seats_in_row=20,
        )
        return theatre_hall

    def create_performance(self):
        play = self.create_play()
        theatre_hall = self.create_theatre_hall()
        performance = Performance.objects.create(
            play=play,
            theatre_hall=theatre_hall,
            show_time=datetime.now()
        )
        return performance

    def create_reservation(self):
        user = self.create_user()
        reservation = Reservation.objects.create(
            created_at=datetime.now(),
            user=user
        )
        return reservation

    def test_actor_str_and_full_name(self):
        actor = Actor.objects.create(
            first_name="Test_name",
            last_name="Test_last_name"
        )
        self.assertEqual(str(actor), actor.first_name + " " + actor.last_name)
        self.assertEqual(actor.full_name,
                         actor.first_name + " " + actor.last_name)

    def test_genre_str(self):
        genre = Genre.objects.create(name="Test_genre")
        self.assertEqual(str(genre), genre.name)

    def test_play_str(self):
        play = self.create_play()
        self.assertEqual(str(play), play.title)

    def test_theatre_hall_str_and_capacity(self):
        theatre_hall = self.create_theatre_hall()
        self.assertEqual(str(theatre_hall), theatre_hall.name)
        self.assertEqual(
            theatre_hall.capacity,
            theatre_hall.rows * theatre_hall.seats_in_row
        )

    def test_performance_str(self):
        performance = self.create_performance()
        self.assertEqual(
            str(performance),
            performance.play.title + " " + str(performance.show_time)
        )

    def test_review_str(self):
        play = self.create_play()
        user = self.create_user()
        review = Review.objects.create(
            user=user, play=play, rating=5, comment="Test_comment"
        )
        self.assertEqual(str(review), review.comment)

    def test_play_rating(self):
        play = self.create_play()
        first_user = self.create_user()
        self.assertEqual(play.rating, None)
        first_review = Review.objects.create(
            user=first_user, play=play, rating=5, comment="Test_comment"
        )
        self.assertEqual(play.rating, first_review.rating)
        second_user = get_user_model().objects.create_user(
            email="<SECOND_EMAIL>", password="<PASSWORD>"
        )
        second_review = Review.objects.create(
            user=second_user, play=play, rating=2, comment="Test_comment"
        )
        self.assertEqual(
            play.rating,
            math.ceil((first_review.rating + second_review.rating) / 2)
        )

    def test_reservation_str(self):
        reservation = self.create_reservation()
        self.assertEqual(str(reservation), str(reservation.created_at))

    def test_ticket_str(self):
        reservation = self.create_reservation()
        performance = self.create_performance()
        ticket = Ticket.objects.create(
            performance=performance,
            reservation=reservation,
            row=2,
            seat=2,
        )
        self.assertEqual(
            str(ticket),
            f"({str(ticket.performance)}: "
            f"row {ticket.row}, seat {ticket.seat}",
        )

    def test_ticket_validation(self):
        reservation = self.create_reservation()
        performance = self.create_performance()

        ticket = Ticket(
            performance=performance,
            reservation=reservation,
            row=0,
            seat=2,
        )

        with self.assertRaises(ValidationError) as context:
            ticket.save()
        self.assertIn("row", context.exception.message_dict)
        self.assertIn(
            "must be in available range",
            context.exception.message_dict["row"][0]
        )

        ticket = Ticket(
            performance=performance,
            reservation=reservation,
            row=2,
            seat=120,
        )

        with self.assertRaises(ValidationError) as context:
            ticket.save()
        self.assertIn("seat", context.exception.message_dict)
        self.assertIn(
            "must be in available range",
            context.exception.message_dict["seat"][0]
        )
        ticket_one = Ticket(
            performance=performance,
            reservation=reservation,
            row=2,
            seat=2,
        )
        ticket_two = Ticket(
            performance=performance,
            reservation=reservation,
            row=2,
            seat=2,
        )

        ticket_one.save()
        with self.assertRaises(ValidationError) as context:
            ticket_two.save()
        self.assertIn("__all__", context.exception.message_dict)
        self.assertIn("already exists",
                      context.exception.message_dict["__all__"][0])
