from django.db.models import F, Count
from rest_framework import viewsets

from theatre.models import (
    Actor,
    Genre,
    Review,
    Play,
    Performance,
    Reservation,
    Ticket,
    TheatreHall,
)
from theatre.serializers import (
    ActorSerializer,
    GenreSerializer,
    ReviewSerializer,
    PlaySerializer,
    PerformanceSerializer,
    ReservationSerializer,
    TicketSerializer,
    TheatreHallSerializer,
    PlayListSerializer,
    PlayDetailSerializer,
    PerformanceListSerializer,
    PerformanceDetailSerializer,
)


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer


class PlayViewSet(viewsets.ModelViewSet):
    queryset = Play.objects.all()
    serializer_class = PlaySerializer

    def get_serializer_class(self):
        if self.action == "list":
            return PlayListSerializer
        elif self.action == "retrieve":
            return PlayDetailSerializer
        return PlaySerializer


class PerformanceViewSet(viewsets.ModelViewSet):
    queryset = (
        Performance.objects.all()
        .select_related("play", "theatre_hall")
        .annotate(
            tickets_available=(
                F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                - Count("tickets")
            )
        )
    )
    serializer_class = PerformanceSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return PerformanceListSerializer
        elif self.action == "retrieve":
            return PerformanceDetailSerializer
        return PerformanceSerializer


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer


class TheatreHallViewSet(viewsets.ModelViewSet):
    queryset = TheatreHall.objects.all()
    serializer_class = TheatreHallSerializer
