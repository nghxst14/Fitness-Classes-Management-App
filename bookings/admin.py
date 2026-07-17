from django.contrib import admin
from django.contrib.auth.models import Group

from .models import Booking, Location, Pack, ServiceType, Session

# Escondemos a aba "Grupos" do admin: só faz sentido com vários funcionários
# de permissões diferentes, e aqui o único utilizador do painel é o Sérgio
# (superuser, que ignora permissões). Para reativar: apagar esta linha.
admin.site.unregister(Group)


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
    fields = ("client", "status")


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


# NOTA: o modelo ClientPack ("Packs dos alunos") já não é registado no admin.
# Era do desenho antigo, em que o saldo vivia dentro de cada pack comprado;
# hoje o saldo são os créditos do utilizador (User.credits). A tabela fica na
# base de dados (evita migração destrutiva), mas escondida não confunde.


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("client", "session", "status", "created_at")
    list_filter = ("status", "session__service_type")
    search_fields = ("client__username", "client__first_name", "client__last_name")
    autocomplete_fields = ("session", "client")
    date_hierarchy = "created_at"
