from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from theatre.models import (
    Actor,
    Genre,
    Review,
    Play,
    Performance,
    Reservation,
    TheatreHall,
)
from theatre.permissions import IsAdminOrIfAuthenticatedReadOnly
from theatre.serializers import (
    ActorSerializer,
    GenreSerializer,
    ReviewSerializer,
    PlaySerializer,
    PerformanceSerializer,
    ReservationSerializer,
    TheatreHallSerializer,
    PlayListSerializer,
    PlayDetailSerializer,
    PerformanceListSerializer,
    PerformanceDetailSerializer,
    ReservationListSerializer,
    ReviewListSerializer,
    ReviewDetailSerializer, PlayImageSerializer
)


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("play")
    serializer_class = ReviewSerializer
    http_method_names = ["get", "post", "head", "delete"]

    def get_serializer_class(self):
        if self.action == "list":
            return ReviewListSerializer
        elif self.action == "retrieve":
            return ReviewDetailSerializer
        return ReviewSerializer

    def get_queryset(self):
        play_id_str = self.request.query_params.get("play")
        queryset = self.queryset

        if play_id_str:
            queryset = queryset.filter(play_id=int(play_id_str))
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        if self.action in ("list", "retrieve", "create"):
            permission_classes = [IsAuthenticated]
        elif self.action == "destroy":
            permission_classes = [IsAdminUser]
        else:
            permission_classes = []
        return [permission() for permission in permission_classes]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="play",
                type={"type": "int"},
                description="Filter by play id (ex. ?play=1)",
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get list of performances."""
        return super().list(request, *args, **kwargs)

class PlayViewSet(viewsets.ModelViewSet):
    queryset = Play.objects.prefetch_related("genres", "actors")
    serializer_class = PlaySerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        title = self.request.query_params.get("title")
        genres = self.request.query_params.get("genres")
        actors = self.request.query_params.get("actors")

        queryset = self.queryset

        if title:
            queryset = queryset.filter(title__icontains=title)

        if genres:
            genres_ids = self._params_to_ints(genres)
            queryset = queryset.filter(genres__id__in=genres_ids)

        if actors:
            actors_ids = self._params_to_ints(actors)
            queryset = queryset.filter(actors__id__in=actors_ids)

        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="title",
                type={"type": "string"},
                description="Filter by title (ex. ?title=Hamilton)",
            ),
            OpenApiParameter(
                name="actors",
                type={"type": "array", "items": {"type": "number"}},
                description="Filter by actor id (ex. ?actors=2,3)",
            ),
            OpenApiParameter(
                name="genres",
                type={"type": "array", "items": {"type": "number"}},
                description="Filter by genre id (ex. ?genres=2,3)",
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get list of movies."""
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == "list":
            return PlayListSerializer
        elif self.action == "retrieve":
            return PlayDetailSerializer
        elif self.action == "upload_image":
            return PlayImageSerializer
        return PlaySerializer

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading image to specific play"""
        play = self.get_object()
        serializer = self.get_serializer(play, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PerformanceViewSet(viewsets.ModelViewSet):
    queryset = (
        Performance.objects
        .select_related("play", "theatre_hall")
        .annotate(
            tickets_available=(
                F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                - Count("tickets")
            )
        )
    )
    serializer_class = PerformanceSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        date = self.request.query_params.get("date")
        play_id_str = self.request.query_params.get("play")

        queryset = self.queryset

        if date:
            date = datetime.strptime(date, "%Y-%m-%d").date()
            queryset = queryset.filter(show_time__date=date)

        if play_id_str:
            queryset = queryset.filter(play_id=int(play_id_str))

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PerformanceListSerializer
        elif self.action == "retrieve":
            return PerformanceDetailSerializer
        return PerformanceSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="play",
                type={"type": "int"},
                description="Filter by play id (ex. ?play=1)",
            ),
            OpenApiParameter(
                name="date",
                type={"type": "string"},
                description="Filter by date (ex. ?date=2025-12-31)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get list of performances."""
        return super().list(request, *args, **kwargs)


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = (Reservation.objects
                .prefetch_related("tickets__performance__play",
                                  "tickets__performance__theatre_hall",
                                  "user"))
    serializer_class = ReservationSerializer
    http_method_names = ["get", "post", "head", "delete"]

    def get_queryset(self):
        queryset = self.queryset
        user_id_str = self.request.query_params.get("user")
        performance_id_str = self.request.query_params.get(
            "tickets__performance"
        )

        if self.request.user.is_staff:
            if user_id_str:
                queryset = queryset.filter(user__id__contains=int(user_id_str))
            if performance_id_str:
                queryset = queryset.filter(
                    tickets__performance__id__contains=int(performance_id_str)
                )
            return queryset
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return ReservationListSerializer
        return ReservationSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "create"):
            permission_classes = [IsAuthenticated]
        elif self.action == "destroy":
            permission_classes = [IsAdminUser]
        else:
            permission_classes = []
        return [permission() for permission in permission_classes]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="user",
                type={"type": "int"},
                description="Filter by user id (ex. ?user=1)",
            ),
            OpenApiParameter(
                name="performance",
                type={"type": "int"},
                description="Filter by performance id (ex. ?tickets__performance=2)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get list of performances."""
        return super().list(request, *args, **kwargs)

class TheatreHallViewSet(viewsets.ModelViewSet):
    queryset = TheatreHall.objects.all()
    serializer_class = TheatreHallSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)
