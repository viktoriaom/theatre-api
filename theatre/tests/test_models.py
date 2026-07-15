import math
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.exceptions import ValidationError

from theatre.models import (
    Actor,
    Genre,
    Review,
    Ticket,
)

from theatre.tests.helpers import (
    create_and_login_user,
    create_test_play,
    create_test_theatre_hall,
    create_test_performance,
    create_test_reservation
)


class ModelsTests(TestCase):

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
        play = create_test_play()
        self.assertEqual(str(play), play.title)

    def test_theatre_hall_str_and_capacity(self):
        theatre_hall = create_test_theatre_hall()
        self.assertEqual(str(theatre_hall), theatre_hall.name)
        self.assertEqual(
            theatre_hall.capacity,
            theatre_hall.rows * theatre_hall.seats_in_row
        )

    def test_performance_str(self):
        performance = create_test_performance()
        self.assertEqual(
            str(performance),
            performance.play.title + " " + str(performance.show_time)
        )

    def test_review_str(self):
        play = create_test_play()
        user, _ = create_and_login_user()
        review = Review.objects.create(
            user=user, play=play, rating=5, comment="Test_comment"
        )
        self.assertEqual(str(review), review.comment)

    def test_play_rating(self):
        play = create_test_play()
        first_user, _ = create_and_login_user()
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
        reservation = create_test_reservation()
        self.assertEqual(str(reservation), str(reservation.created_at))

    def test_ticket_str(self):
        reservation = create_test_reservation()
        performance = create_test_performance()
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
        reservation = create_test_reservation()
        performance = create_test_performance()

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
