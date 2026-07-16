from django.contrib import admin

from .models import Booking, ClientPack, Location, Pack, ServiceType, Session


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "active")
    list_filter = ("kind", "active")
    search_fields = ("name", "address")


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "default_capacity",
        "is_online",
        "min_cancel_hours",
        "active",
    )
    list_filter = ("is_online", "active")
    search_fields = ("name",)


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    autocomplete_fields = ("client",)
    fields = ("client", "status", "client_pack")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "service_type",
        "location",
        "start",
        "capacity",
        "spots_taken",
        "spots_left",
        "is_cancelled",
    )
    list_filter = ("service_type", "location", "is_cancelled")
    search_fields = ("title", "service_type__name")
    date_hierarchy = "start"
    autocomplete_fields = ("trainer", "location", "service_type")
    inlines = [BookingInline]

    @admin.display(description="Ocupadas")
    def spots_taken(self, obj):
        return obj.spots_taken

    @admin.display(description="Livres")
    def spots_left(self, obj):
        return obj.spots_left


@admin.register(Pack)
class PackAdmin(admin.ModelAdmin):
    list_display = ("name", "number_of_sessions", "price", "order", "active")
    list_editable = ("order", "active")
    list_filter = ("active",)
    search_fields = ("name",)


@admin.register(ClientPack)
class ClientPackAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "pack",
        "sessions_used",
        "sessions_total",
        "sessions_remaining",
        "expires_at",
    )
    list_filter = ("pack",)
    search_fields = ("client__username", "client__first_name", "client__last_name")
    autocomplete_fields = ("client", "pack")

    @admin.display(description="Restantes")
    def sessions_remaining(self, obj):
        return obj.sessions_remaining


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("client", "session", "status", "created_at")
    list_filter = ("status", "session__service_type")
    search_fields = ("client__username", "client__first_name", "client__last_name")
    autocomplete_fields = ("session", "client", "client_pack")
    date_hierarchy = "created_at"
