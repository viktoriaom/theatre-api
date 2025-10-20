from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from theatre.models import (
    Actor,
    Genre,
    TheatreHall,
    Play,
    Performance,
    Ticket,
    Reservation,
    Review,
)


class ActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = ["id", "first_name", "last_name", "full_name"]


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name"]


class TheatreHallSerializer(serializers.ModelSerializer):
    class Meta:
        model = TheatreHall
        fields = ["id", "name", "rows", "seats_in_row", "capacity"]


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "play", "rating", "comment"]


class PlaySerializer(serializers.ModelSerializer):
    reviews = ReviewSerializer(many=True, read_only=True)
    rating = serializers.SerializerMethodField()

    class Meta:
        model = Play
        fields = ["id",
                  "title",
                  "description",
                  "genres",
                  "actors",
                  "rating",
                  "reviews"]

    def get_rating(self, obj):
        return obj.rating


class PlayListSerializer(serializers.ModelSerializer):
    rating = serializers.SerializerMethodField()
    genres = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name"
    )
    actors = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="full_name"
    )

    class Meta:
        model = Play
        fields = ["id", "title", "description", "genres", "actors", "rating"]

    def get_rating(self, obj):
        return obj.rating


class PlayDetailSerializer(serializers.ModelSerializer):
    rating = serializers.SerializerMethodField()
    genres = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name"
    )
    actors = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="full_name"
    )
    reviews = ReviewSerializer(many=True)

    class Meta:
        model = Play
        fields = ["id",
                  "title",
                  "description",
                  "genres",
                  "actors",
                  "rating",
                  "reviews"]

    def get_rating(self, obj):
        return obj.rating


class PerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Performance
        fields = ["id", "play", "theatre_hall", "show_time"]


class PerformanceListSerializer(serializers.ModelSerializer):
    play_title = serializers.CharField(source="play.title", read_only=True)
    theatre_hall_name = serializers.CharField(
        source="theatre_hall.name", read_only=True
    )
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Performance
        fields = [
            "id",
            "play_title",
            "theatre_hall_name",
            "show_time",
            "tickets_available",
        ]


class PerformanceDetailSerializer(serializers.ModelSerializer):
    play_title = serializers.CharField(source="play.title", read_only=True)
    play_description = serializers.CharField(
        source="play.description",
        read_only=True)
    play_rating = serializers.CharField(source="play.rating", read_only=True)
    theatre_hall_name = serializers.CharField(
        source="theatre_hall.name", read_only=True
    )
    theatre_hall_capacity = serializers.IntegerField(
        source="theatre_hall.capacity", read_only=True
    )
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Performance
        fields = [
            "id",
            "play_title",
            "play_description",
            "play_rating",
            "theatre_hall_name",
            "theatre_hall_capacity",
            "show_time",
            "tickets_available",
        ]


class TicketSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super(TicketSerializer, self).validate(attrs=attrs)
        Ticket.validate_ticket(
            attrs["row"],
            attrs["seat"],
            attrs["movie_session"].cinema_hall,
            ValidationError,
        )
        return data

    class Meta:
        model = Ticket
        fields = ["id", "row", "seat", "performance", "reservation"]


class ReservationSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Reservation
        fields = ["id", "created_at", "user", "tickets"]

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            reservation = Reservation.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(reservation=reservation, **ticket_data)
            return reservation
