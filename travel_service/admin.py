from django.contrib import admin

from travel_service.models import (
    Ticket,
    Train,
    TrainType,
    Station,
    Route,
    Crew,
    Journey,
    Order
)


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [
        TicketInline,
    ]


admin.site.register(Station)
admin.site.register(Train)
admin.site.register(TrainType)
admin.site.register(Route)
admin.site.register(Crew)
admin.site.register(Journey)
