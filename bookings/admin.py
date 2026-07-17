from django.contrib import admin
from django.contrib.auth.models import Group
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

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


class CheckboxFilter(admin.SimpleListFilter):
    """
    Base para filtros de multi-seleção com checkboxes.

    O admin nativo só suporta escolha única (links). Aqui, o valor no URL é
    uma lista separada por vírgulas (?estado=agendada,cancelada) e cada
    checkbox liga/desliga a sua opção. O template está em
    templates/admin/checkbox_filter.html.
    """

    template = "admin/checkbox_filter.html"

    def value_list(self):
        """As opções atualmente selecionadas, como lista."""
        return self.value().split(",") if self.value() else []

    def choices(self, changelist):
        selected = set(self.value_list())
        for lookup, title in self.lookup_choices:
            # URL que este checkbox aponta: o estado atual com esta opção
            # invertida (ligada se estava desligada, e vice-versa).
            nova = selected ^ {lookup}
            if nova:
                query = changelist.get_query_string(
                    {self.parameter_name: ",".join(sorted(nova))}
                )
            else:
                query = changelist.get_query_string(remove=[self.parameter_name])
            yield {
                "selected": lookup in selected,
                "query_string": query,
                "display": title,
            }


class EstadoFilter(CheckboxFilter):
    """Filtra por estado da sessão (combinável: ex. agendadas + canceladas)."""

    title = "estado"
    parameter_name = "estado"

    def lookups(self, request, model_admin):
        return [
            ("agendada", "Agendadas"),
            ("concluida", "Concluídas"),
            ("cancelada", "Canceladas"),
        ]

    def queryset(self, request, queryset):
        selecionados = self.value_list()
        if not selecionados:
            return queryset
        agora = timezone.now()
        cond = Q()
        if "agendada" in selecionados:
            cond |= Q(is_cancelled=False, start__gte=agora)
        if "concluida" in selecionados:
            cond |= Q(is_cancelled=False, start__lt=agora)
        if "cancelada" in selecionados:
            cond |= Q(is_cancelled=True)
        return queryset.filter(cond)


class TempoFilter(CheckboxFilter):
    """Filtra por tempo (futuras/passadas), combinável com o estado."""

    title = "tempo"
    parameter_name = "tempo"

    def lookups(self, request, model_admin):
        return [("futuras", "Futuras"), ("passadas", "Passadas")]

    def queryset(self, request, queryset):
        selecionados = self.value_list()
        if not selecionados:
            return queryset
        agora = timezone.now()
        cond = Q()
        if "futuras" in selecionados:
            cond |= Q(start__gte=agora)
        if "passadas" in selecionados:
            cond |= Q(start__lt=agora)
        return queryset.filter(cond)


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
        "inscritos",
        "estado",
    )
    # Mais recentes primeiro: sem isto, as aulas mais ANTIGAS apareciam no
    # topo e o Sérgio teria de paginar até chegar à semana atual.
    ordering = ("-start",)
    list_filter = (EstadoFilter, TempoFilter, "service_type", "location")
    search_fields = ("title", "service_type__name")
    date_hierarchy = "start"
    autocomplete_fields = ("trainer", "location", "service_type")
    inlines = [BookingInline]

    @admin.display(description="Estado")
    def estado(self, obj):
        """
        Estado legível em vez do booleano is_cancelled invertido (que mostrava
        uma cruz vermelha em aulas perfeitamente normais). O vermelho fica
        reservado para o único caso realmente negativo: cancelada.
        """
        if obj.is_cancelled:
            return format_html('<span style="color:#ba2121;">✘ Cancelada</span>')
        if obj.is_past:
            return format_html('<span style="color:#888;">Concluída</span>')
        return format_html('<span style="color:#1c7430;">✔ Agendada</span>')

    @admin.display(description="Inscritos")
    def inscritos(self, obj):
        """
        "3 / 12" clicável: leva às Marcações filtradas por esta aula, onde
        se veem os nomes (e onde um dia se marcam presenças/faltas).
        Substitui as antigas colunas Lotação/Ocupadas/Livres, que diziam
        variações da mesma coisa em três colunas.
        """
        url = (
            reverse("admin:bookings_booking_changelist")
            + f"?session__id__exact={obj.pk}"
        )
        return format_html(
            '<a href="{}">{} / {}</a>', url, obj.spots_taken, obj.capacity
        )


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

    def lookup_allowed(self, lookup, value, request=None):
        # Autoriza o filtro por sessão vindo da coluna "Inscritos" da lista
        # de Sessões (o admin bloqueia lookups não declarados, por segurança).
        if lookup == "session__id__exact":
            return True
        return super().lookup_allowed(lookup, value, request)
