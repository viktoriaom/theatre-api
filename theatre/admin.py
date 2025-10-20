from django.contrib import admin

from theatre.models import (
    Performance,
    Review,
    Ticket,
    TheatreHall,
    Reservation,
    Play,
    Actor,
    Genre
)


admin.site.register(TheatreHall)
admin.site.register(Genre)
admin.site.register(Actor)
admin.site.register(Play)
admin.site.register(Performance)
admin.site.register(Reservation)
admin.site.register(Review)
admin.site.register(Ticket)
