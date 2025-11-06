from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory
from theatre.models import Review
from theatre.serializers import (
    ReviewListSerializer,
    ReviewDetailSerializer,
    ReviewSerializer,
)
from theatre.views import ReviewViewSet

from theatre_api import settings
from theatre.tests.helpers import (
    create_and_login_user,
    create_test_play,
    create_test_review
)

REVIEW_URL = reverse("theatre:reviews-list")
PAGE_SIZE = settings.REST_FRAMEWORK.get("PAGE_SIZE", 10)


def detail_url(review_id):
    return reverse("theatre:reviews-detail", kwargs={"pk": review_id})


class UnauthenticatedReviewViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(REVIEW_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedReviewViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user, self.client = create_and_login_user()

    def test_list_reviews(self):
        create_test_review()
        create_test_review()
        res = self.client.get(REVIEW_URL)
        reviews = Review.objects.all()
        serializer = ReviewListSerializer(reviews, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_paginated_list_reviews(self):
        reviews_count = PAGE_SIZE + (PAGE_SIZE // 2)
        for _ in range(reviews_count):
            create_test_review()
        res = self.client.get(REVIEW_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertIn("count", res.data)
        self.assertIn("next", res.data)
        self.assertIn("previous", res.data)
        self.assertEqual(len(res.data["results"]), PAGE_SIZE)
        self.assertEqual(res.data["count"], reviews_count)
        self.assertIsNotNone(res.data["next"])
        self.assertIsNone(res.data["previous"])
        res_page_2 = self.client.get(
            REVIEW_URL, {"limit": PAGE_SIZE, "offset": PAGE_SIZE}
        )
        self.assertEqual(res_page_2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_page_2.data["results"]),
                         reviews_count - PAGE_SIZE)
        self.assertIsNone(res_page_2.data["next"])
        self.assertIsNotNone(res_page_2.data["previous"])

    def test_filter_reviews_by_play_id(self):
        play_one = create_test_play()
        play_two = create_test_play()
        review_one = create_test_review(user=self.user, play=play_one)
        review_two = create_test_review(user=self.user, play=play_two)

        res = self.client.get(REVIEW_URL, {"play": f"{play_one.id}"})
        serializer_one = ReviewListSerializer(review_one)
        serializer_two = ReviewListSerializer(review_two)

        self.assertIn(serializer_one.data, res.data["results"])
        self.assertNotIn(serializer_two.data, res.data["results"])

    def test_detail_review(self):
        review = create_test_review(user=self.user)
        res = self.client.get(detail_url(review.id))
        serializer = ReviewDetailSerializer(review)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_test_review(self):
        play = create_test_play()
        payload = {
            "play": play.id,
            "rating": 5,
            "comment": "test comment",
        }
        res = self.client.post(REVIEW_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        review = Review.objects.get(id=res.data["id"])
        self.assertEqual(review.comment, payload["comment"])
        self.assertEqual(review.rating, payload["rating"])
        self.assertEqual(review.play.id, payload["play"])
        self.assertEqual(review.user, self.user)
        play = create_test_play()
        payload = {
            "play": play.id,
            "rating": 1,
            "comment": "test comment",
        }
        res = self.client.post(REVIEW_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_wrong_rating_values_forbidden(self):
        play = create_test_play()
        payload_with_wrong_rating = {
            "play": play.id,
            "rating": 999,
            "comment": "test comment",
        }
        res = self.client.post(REVIEW_URL, payload_with_wrong_rating)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rating", res.data)
        payload_with_zero_rating = {
            "play": play.id,
            "rating": 0,
            "comment": "test comment",
        }
        res = self.client.post(REVIEW_URL, payload_with_zero_rating)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rating", res.data)

    def test_no_comment_forbidden(self):
        play = create_test_play()
        payload_with_no_comment = {
            "play": play.id,
            "rating": 5,
            "comment": "",
        }
        res = self.client.post(REVIEW_URL, payload_with_no_comment)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("comment", res.data)

    def test_prevent_duplicate_review_same_user_play(self):
        play = create_test_play()
        payload = {
            "play": play.id,
            "rating": 5,
            "comment": "good comment",
        }
        res = self.client.post(REVIEW_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res = self.client.post(REVIEW_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_review_forbidden(self):
        review = create_test_review(user=self.user)
        play = create_test_play()
        payload = {
            "play": play.id,
            "rating": 5,
            "comment": "NewReviewComment",
        }
        review_to_put_url = detail_url(review.id)
        res = self.client.put(review_to_put_url, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_review_forbidden(self):
        review = create_test_review(user=self.user)
        payload = {
            "comment": "NewReviewComment",
        }
        review_to_patch_url = detail_url(review.id)
        res = self.client.patch(review_to_patch_url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_review_forbidden(self):
        review = create_test_review(user=self.user)
        serializer = ReviewListSerializer(review)
        res = self.client.get(REVIEW_URL)
        self.assertIn(serializer.data, res.data["results"])
        review_to_delete_url = detail_url(review.id)
        res = self.client.delete(review_to_delete_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminReviewViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user, self.client = create_and_login_user(
            email="admin@example.com", is_staff=True
        )

    def test_put_review_admin_forbidden(self):
        review = create_test_review(user=self.user)
        play = create_test_play()
        payload = {
            "play": play.id,
            "rating": 5,
            "comment": "NewReviewComment",
        }
        review_to_put_url = detail_url(review.id)
        res = self.client.put(review_to_put_url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_review_admin_forbidden(self):
        review = create_test_review(user=self.user)
        payload = {
            "comment": "NewReviewDescription",
        }
        review_to_patch_url = detail_url(review.id)
        res = self.client.patch(review_to_patch_url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_review_admin(self):
        another_user = get_user_model().objects.create_user(
            email="test_user@example.com",
            password="testuser",
            is_staff=False,
        )
        review = create_test_review(user=another_user)
        serializer = ReviewListSerializer(review)

        res = self.client.get(REVIEW_URL)
        self.assertIn(serializer.data, res.data["results"])

        review_to_delete_url = detail_url(review.id)
        res = self.client.delete(review_to_delete_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)


class ReviewViewSetSerializerClassTest(TestCase):
    def setUp(self):
        self.viewset = ReviewViewSet()
        self.factory = APIRequestFactory()
        self.request = self.factory.get(REVIEW_URL)
        self.viewset.request = self.request

    def test_list_action_uses_list_serializer(self):
        self.viewset.action = "list"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, ReviewListSerializer)

    def test_retrieve_action_uses_detail_serializer(self):
        self.viewset.action = "retrieve"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, ReviewDetailSerializer)

    def test_default_action_uses_base_serializer(self):
        self.viewset.action = "create"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, ReviewSerializer)
