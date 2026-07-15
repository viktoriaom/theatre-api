from django.urls import path, include
from rest_framework import routers

from theatre.views import (
    GenreViewSet,
    ActorViewSet,
    TheatreHallViewSet,
    PlayViewSet,
    PerformanceViewSet,
    ReservationViewSet,
    ReviewViewSet
)

router = routers.DefaultRouter()
router.register("genres", GenreViewSet, basename="genres")
router.register("actors", ActorViewSet, basename="actors")
router.register("theatre_halls", TheatreHallViewSet, basename="theatre_halls")
router.register("plays", PlayViewSet, basename="plays")
router.register("performances", PerformanceViewSet, basename="performances")
router.register("reservations", ReservationViewSet, basename="reservations")
router.register("reviews", ReviewViewSet, basename="reviews")

urlpatterns = [path("", include(router.urls))]

app_name = "theatre"
