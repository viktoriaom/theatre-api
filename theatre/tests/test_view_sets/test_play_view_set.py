from io import BytesIO
from PIL import Image
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from theatre.models import Play, Actor, Genre
from theatre.serializers import (
    PlayListSerializer,
    PlayDetailSerializer,
    PlayImageSerializer,
    PlaySerializer,
)
from theatre.views import PlayViewSet
from theatre_api import settings
from theatre.tests.helpers import (
    create_and_login_user,
    create_test_play
)

PAGE_SIZE = settings.base.REST_FRAMEWORK.get("PAGE_SIZE", 10)
PLAY_URL = reverse("theatre:plays-list")


def detail_url(play_id):
    return reverse("theatre:plays-detail", kwargs={"pk": play_id})


class UnauthenticatedPlayViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(PLAY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedPlayViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user, self.client = create_and_login_user()

    def test_list_plays(self):
        create_test_play()
        res = self.client.get(PLAY_URL)
        plays = Play.objects.all()
        serializer = PlayListSerializer(plays, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_paginated_list_plays(self):
        plays_count = PAGE_SIZE + (PAGE_SIZE // 2)
        for _ in range(plays_count):
            create_test_play()
        res = self.client.get(PLAY_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertIn("count", res.data)
        self.assertIn("next", res.data)
        self.assertIn("previous", res.data)
        self.assertEqual(len(res.data["results"]), PAGE_SIZE)
        self.assertEqual(res.data["count"], plays_count)
        self.assertIsNotNone(res.data["next"])
        self.assertIsNone(res.data["previous"])
        res_page_2 = self.client.get(
            PLAY_URL, {"limit": PAGE_SIZE, "offset": PAGE_SIZE}
        )
        self.assertEqual(res_page_2.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(res_page_2.data["results"]),
            plays_count - PAGE_SIZE
        )
        self.assertIsNone(res_page_2.data["next"])
        self.assertIsNotNone(res_page_2.data["previous"])

    def test_filter_by_title_plays(self):
        play_one = create_test_play(title="Moulin Rouge")
        play_two = create_test_play(title="Lion King")

        res = self.client.get(PLAY_URL, {"title": f"{play_one.title}"})
        serializer_one = PlayListSerializer(play_one)
        serializer_two = PlayListSerializer(play_two)

        self.assertIn(serializer_one.data, res.data["results"])
        self.assertNotIn(serializer_two.data, res.data["results"])

        res = self.client.get(PLAY_URL, {"title": "mo"})
        self.assertIn(serializer_one.data, res.data["results"])
        self.assertNotIn(serializer_two.data, res.data["results"])

    def test_filter_by_actor_plays(self):
        play_one = create_test_play()
        play_two = create_test_play()

        actor_one = Actor.objects.create(
            first_name="Ewan",
            last_name="McGregor"
        )
        actor_two = Actor.objects.create(
            first_name="Leonardo",
            last_name="DiCaprio"
        )

        play_one.actors.add(actor_one)
        play_two.actors.add(actor_two)

        res = self.client.get(PLAY_URL, {"actors": f"{actor_one.id}"})

        serializer_one = PlayListSerializer(play_one)
        serializer_two = PlayListSerializer(play_two)

        self.assertIn(serializer_one.data, res.data["results"])
        self.assertNotIn(serializer_two.data, res.data["results"])

    def test_filter_by_genre_plays(self):
        play_one = create_test_play()
        play_two = create_test_play()

        genre_one = Genre.objects.create(name="musical")
        genre_two = Genre.objects.create(name="kid-friendly")

        play_one.genres.add(genre_one)
        play_two.genres.add(genre_two)

        res = self.client.get(PLAY_URL, {"genres": f"{genre_one.id}"})

        serializer_one = PlayListSerializer(play_one)
        serializer_two = PlayListSerializer(play_two)

        self.assertIn(serializer_one.data, res.data["results"])
        self.assertNotIn(serializer_two.data, res.data["results"])

    def test_detail_play(self):
        play = create_test_play()
        res = self.client.get(detail_url(play.id))
        serializer = PlayDetailSerializer(play)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_play_not_admin_forbidden(self):
        payload = {
            "title": "Moulin Rouge",
            "description": "PlayDescription",
        }
        res = self.client.post(PLAY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_play_not_admin_forbidden(self):
        play = create_test_play()
        payload = {
            "title": "NewPlayTitle",
            "description": "NewPlayDescription",
        }
        play_to_put_url = detail_url(play.id)
        res = self.client.put(play_to_put_url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_play_not_admin_forbidden(self):
        play = create_test_play()
        payload = {
            "description": "NewPlayDescription",
        }
        play_to_patch_url = detail_url(play.id)
        res = self.client.patch(play_to_patch_url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_play_image_not_admin_forbidden(self):
        play = create_test_play()
        url = reverse("theatre:plays-upload-image", kwargs={"pk": play.id})
        image = SimpleUploadedFile(
            name="test.jpg",
            content=b"fake-image-content",
            content_type="image/jpeg"
        )
        res = self.client.post(url, {"image": image}, format="multipart")
        play.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminPlayViewSetTests(TestCase):
    def setUp(self):
        self.user, self.client = create_and_login_user(
            email="admin@example.com", is_staff=True
        )

    def test_create_play_admin(self):
        genre = Genre.objects.create(name="action")
        actor = Actor.objects.create(first_name="Ewan", last_name="McGregor")
        payload = {
            "title": "Moulin Rouge",
            "description": "PlayDescription",
            "actors": [actor.id],
            "genres": [genre.id],
        }
        res = self.client.post(PLAY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        play = Play.objects.get(title="Moulin Rouge")
        self.assertEqual(play.title, payload["title"])
        self.assertEqual(play.description, payload["description"])
        self.assertEqual(play.actors.count(), 1)
        self.assertEqual(play.genres.count(), 1)
        self.assertIn(genre, play.genres.all())
        self.assertIn(actor, play.actors.all())

    def test_create_invalid_play(self):
        payload_with_zero_title = {
            "title": "",
            "description": "PlayDescription",
        }
        payload_with_zero_description = {
            "title": "Title",
            "description": "",
        }
        payload_with_wrong_actors = {
            "title": "Title",
            "description": "PlayDescription",
            "actors": 0,
        }
        payload_with_wrong_genres = {
            "title": "Title",
            "description": "PlayDescription",
            "genres": 0,
        }
        payload_for_same_title = {
            "title": "The same title",
            "description": "PlayDescription",
        }
        res = self.client.post(PLAY_URL, payload_with_zero_title)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = self.client.post(PLAY_URL, payload_with_zero_description)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = self.client.post(PLAY_URL, payload_with_wrong_actors)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = self.client.post(PLAY_URL, payload_with_wrong_genres)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        res = self.client.post(PLAY_URL, payload_for_same_title)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res = self.client.post(PLAY_URL, payload_for_same_title)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_play_admin(self):
        play = create_test_play()
        payload = {
            "title": "NewPlayTitle",
            "description": "NewPlayDescription",
        }
        play_to_put_url = detail_url(play.id)
        res = self.client.put(play_to_put_url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        play.refresh_from_db()
        self.assertEqual(payload["title"], play.title)
        self.assertEqual(payload["description"], play.description)

        self.assertEqual(res.data["title"], payload["title"])
        self.assertEqual(res.data["description"], payload["description"])

    def test_patch_play_admin(self):
        play = create_test_play()
        payload = {
            "description": "NewPlayDescription",
        }
        play_to_patch_url = detail_url(play.id)
        res = self.client.patch(play_to_patch_url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        play.refresh_from_db()
        self.assertEqual(res.data["description"], payload["description"])

    def test_delete_play_admin(self):
        play = create_test_play()
        serializer = PlayListSerializer(play)
        res = self.client.get(PLAY_URL)
        self.assertIn(serializer.data, res.data["results"])
        play_to_delete_url = detail_url(play.id)
        res = self.client.delete(play_to_delete_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_add_play_image_admin(self):
        play = create_test_play()
        url = reverse("theatre:plays-upload-image", kwargs={"pk": play.id})
        image_io = BytesIO()
        image = Image.new("RGB", (100, 100), color="red")
        image.save(image_io, format="JPEG")
        image_io.seek(0)
        uploaded_image = SimpleUploadedFile(
            name="test.jpg", content=image_io.read(), content_type="image/jpeg"
        )

        res = self.client.post(
            url,
            {"image": uploaded_image},
            format="multipart"
        )
        play.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(play.image.name.endswith(".jpg"))


class PlayViewSetSerializerClassTest(TestCase):
    def setUp(self):
        self.viewset = PlayViewSet()

    def test_list_action_uses_list_serializer(self):
        self.viewset.action = "list"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, PlayListSerializer)

    def test_retrieve_action_uses_detail_serializer(self):
        self.viewset.action = "retrieve"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, PlayDetailSerializer)

    def test_upload_image_action_uses_image_serializer(self):
        self.viewset.action = "upload_image"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, PlayImageSerializer)

    def test_default_action_uses_base_serializer(self):
        self.viewset.action = "create"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, PlaySerializer)
