import re

from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
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
        "credit_type",
        "default_capacity",
        "is_online",
        "min_cancel_hours",
        "active",
    )
    list_filter = ("credit_type", "is_online", "active")
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
    autocomplete_fields = ("location", "service_type")
    inlines = [BookingInline]
    # Cancelar NÃO tem ação em massa (decisão após um cancelamento acidental
    # com seleção múltipla): faz-se aula a aula, pelo botão na ficha da
    # sessão, com confirmação. Reativar mantém-se em massa (não mexe em
    # créditos, e serve o caso "chuva que afinal passou").
    actions = ["reativar_sessoes"]
    # O checkbox is_cancelled sai do formulário pela mesma razão — o único
    # caminho para cancelar é o botão explícito. O estado fica visível
    # em leitura. O campo trainer sai porque só há um treinador (o Sérgio);
    # o campo fica no modelo, escondido, caso um dia haja mais.
    exclude = ("is_cancelled", "trainer")
    readonly_fields = ("estado",)

    def get_urls(self):
        """Rotas dos botões Cancelar/Reativar da ficha da sessão."""
        rotas = [
            path(
                "<path:object_id>/cancelar/",
                self.admin_site.admin_view(self.cancelar_view),
                name="bookings_session_cancelar",
            ),
            path(
                "<path:object_id>/reativar/",
                self.admin_site.admin_view(self.reativar_view),
                name="bookings_session_reativar",
            ),
        ]
        return rotas + super().get_urls()

    def cancelar_view(self, request, object_id):
        """Cancela UMA aula (botão na ficha, com confirmação no browser)."""
        sessao = get_object_or_404(Session, pk=object_id)
        if not self.has_change_permission(request, sessao):
            raise PermissionDenied
        if request.method == "POST":
            if sessao.is_cancelled:
                self.message_user(
                    request, "Esta aula já está cancelada.", messages.WARNING
                )
            else:
                creditos = sessao.bookings.filter(status=Booking.BOOKED).count()
                sessao.is_cancelled = True
                sessao.save()  # dispara o reembolso automático
                self.message_user(
                    request,
                    f"Aula cancelada; {creditos} crédito(s) devolvido(s) aos "
                    "alunos. Não te esqueças de os avisar.",
                    messages.SUCCESS,
                )
        return redirect("admin:bookings_session_change", object_id)

    def reativar_view(self, request, object_id):
        """Reativa UMA aula (sem inscrever ninguém automaticamente)."""
        sessao = get_object_or_404(Session, pk=object_id)
        if not self.has_change_permission(request, sessao):
            raise PermissionDenied
        if request.method == "POST":
            if not sessao.is_cancelled:
                self.message_user(
                    request, "Esta aula não está cancelada.", messages.WARNING
                )
            else:
                antigas = sessao.bookings.filter(status=Booking.CANCELLED).count()
                sessao.is_cancelled = False
                sessao.save()
                self.message_user(
                    request,
                    "Aula reativada. Ninguém foi inscrito automaticamente — "
                    f"há {antigas} marcação(ões) cancelada(s) associada(s); "
                    "avisa os alunos para se reinscreverem.",
                    messages.SUCCESS,
                )
        return redirect("admin:bookings_session_change", object_id)

    @admin.action(description="Reativar selecionadas")
    def reativar_sessoes(self, request, queryset):
        """
        Reativa sem inscrever ninguém automaticamente: os alunos foram
        reembolsados no cancelamento e decidem eles se voltam (a app
        suporta reinscrição na mesma aula). O Sérgio avisa-os — as
        marcações canceladas ficam visíveis na ficha da sessão e nas
        Marcações, com o atalho de WhatsApp.
        """
        reativadas = antigas = 0
        for sessao in queryset.filter(is_cancelled=True):
            antigas += sessao.bookings.filter(status=Booking.CANCELLED).count()
            sessao.is_cancelled = False
            sessao.save()
            reativadas += 1
        if reativadas:
            self.message_user(
                request,
                f"{reativadas} sessão(ões) reativada(s). Ninguém foi inscrito "
                f"automaticamente — há {antigas} marcação(ões) cancelada(s) "
                "associada(s); avisa os alunos para se reinscreverem.",
                messages.SUCCESS,
            )
        else:
            self.message_user(
                request, "Nenhuma sessão cancelada na seleção.", messages.WARNING
            )

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
    list_display = (
        "name", "credit_type", "number_of_sessions", "price", "order", "active"
    )
    list_editable = ("order", "active")
    list_filter = ("credit_type", "active")
    search_fields = ("name",)


# NOTA: o modelo ClientPack ("Packs dos alunos") já não é registado no admin.
# Era do desenho antigo, em que o saldo vivia dentro de cada pack comprado;
# hoje o saldo são os créditos do utilizador (User.credits). A tabela fica na
# base de dados (evita migração destrutiva), mas escondida não confunde.


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("client", "telemovel", "session", "status", "created_at")
    list_filter = ("status", "session__service_type")
    search_fields = ("client__username", "client__first_name", "client__last_name")
    autocomplete_fields = ("session", "client")
    date_hierarchy = "created_at"

    @admin.display(description="Telemóvel")
    def telemovel(self, obj):
        """
        O número do aluno; clicar pergunta se quer abrir a conversa no
        WhatsApp com ele (confirm nativo do browser) e, se sim, abre o
        wa.me numa aba nova. Contas cujo username não é um número
        (ex.: admin) aparecem sem link.
        """
        numero = obj.client.username
        if not re.fullmatch(r"9\d{8}", numero):
            return numero
        nome = obj.client.get_full_name() or numero
        return format_html(
            '<a href="https://wa.me/351{}" target="_blank" rel="noopener" '
            'onclick="return confirm(\'Abrir conversa no WhatsApp com {}?\')">{}</a>',
            numero, nome, numero,
        )

    def lookup_allowed(self, lookup, value, request=None):
        # Autoriza o filtro por sessão vindo da coluna "Inscritos" da lista
        # de Sessões (o admin bloqueia lookups não declarados, por segurança).
        if lookup == "session__id__exact":
            return True
        return super().lookup_allowed(lookup, value, request)
