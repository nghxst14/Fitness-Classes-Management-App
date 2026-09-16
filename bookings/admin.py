import re
from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.widgets import AdminDateWidget, AdminSplitDateTime
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Booking,
    ListaEspera,
    Location,
    MovimentoCredito,
    Pack,
    ServiceType,
    Session,
    WeeklyProgramSlot,
)


class HoraWidget(forms.Widget):
    """
    Hora em duas caixas: [hora] : [minuto]. A hora aceita 0-23 e o minuto
    sugere 00/15/30/45, mas ambas permitem escrita livre (ex.: 13:02).
    Substitui a caixa única onde era preciso escrever "21:00" à mão.
    """

    template_name = "admin/widgets/hora.html"

    def _split(self, value):
        """Parte o valor (datetime.time ou string 'HH:MM...') em hora, minuto."""
        if value in (None, ""):
            return "", ""
        if isinstance(value, str):
            partes = value.split(":")
            return partes[0], (partes[1] if len(partes) > 1 else "")
        return str(value.hour), f"{value.minute:02d}"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        hora, minuto = self._split(value)
        context["widget"]["hora"] = hora
        context["widget"]["minuto"] = minuto
        context["widget"]["horas_lista"] = list(range(24))
        return context

    def value_from_datadict(self, data, files, name):
        hora = (data.get(f"{name}_h") or "").strip()
        minuto = (data.get(f"{name}_m") or "").strip()
        if not hora and not minuto:
            return ""
        return f"{hora or 0}:{minuto or 0}"


class AdminSplitDateTimeHora(AdminSplitDateTime):
    """Como o seletor data+hora do admin, mas com a hora em duas caixas."""

    # Template próprio que empilha a hora por baixo da data (o do admin usa
    # <br>, que não quebra dentro da linha flex do campo).
    template_name = "admin/widgets/split_datetime_hora.html"

    def __init__(self, attrs=None):
        # Mantém o seletor de data (AdminDateWidget: "Hoje" + calendário) e
        # troca só a parte da hora pelo HoraWidget.
        forms.MultiWidget.__init__(self, [AdminDateWidget, HoraWidget], attrs)

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
        "capacity",
        "start",
        "inscritos",
        "estado",
    )

    def get_queryset(self, request):
        """
        Traz o tipo, o local e a contagem de inscritos na mesma consulta.

        Este ecrã mostra 100 aulas de cada vez e cada linha tem a coluna
        "Inscritos": sem isto era uma ida à base de dados por linha, só para
        escrever "3 / 12".
        """
        return (
            super()
            .get_queryset(request)
            .select_related("service_type", "location")
            .com_inscritos()
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Congela as opções dos menus da lista editável numa lista.

        O `list_editable` põe um menu de Tipo e outro de Local em **cada**
        linha. O campo é o mesmo para todas, mas desenhá-lo vai buscar as
        opções à base de dados de cada vez — outra consulta por linha, e
        desta vez só para escrever os mesmos três tipos e quatro locais 100
        vezes. Avaliadas uma vez aqui, todas as linhas reutilizam a lista.
        """
        campo = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name in ("service_type", "location"):
            campo.choices = list(campo.choices)
        return campo
    # Editar na própria lista: o programa semanal é o molde, mas há sempre o
    # imprevisto de última hora (a aula de amanhã muda de local). Assim o
    # Sérgio corrige várias de uma vez e grava uma só. A hora fica de fora de
    # propósito — mudá-la é mudar a aula, e isso faz-se na ficha.
    list_editable = ("service_type", "location", "capacity")
    # Mais recentes primeiro: sem isto, as aulas mais ANTIGAS apareciam no
    # topo e o Sérgio teria de paginar até chegar à semana atual.
    ordering = ("-start",)
    list_filter = (EstadoFilter, TempoFilter, "service_type", "location")
    search_fields = ("title", "service_type__name")
    date_hierarchy = "start"
    # NOTA: o autocomplete_fields foi retirado (ago 2026). O widget de pesquisa
    # existe para escolher entre centenas de opções; aqui são 3 tipos de
    # serviço e 4 locais. Uma caixa normal abre logo, sem ir buscar nada ao
    # servidor — e, ao contrário do select2, encolhe com o ecrã (o select2
    # gravava uma largura fixa que saía fora da margem no telemóvel). Com uma
    # coluna editável por linha na lista, a diferença nota-se ainda mais.
    inlines = [BookingInline]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # A hora do início passa a ter duas caixas (hora : minuto), em vez da
        # caixa única onde era preciso escrever "21:00" à mão.
        if db_field.name == "start":
            return forms.SplitDateTimeField(
                label=db_field.verbose_name,
                widget=AdminSplitDateTimeHora(),
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    # Cancelar em massa tem uma PÁGINA DE CONFIRMAÇÃO (ao contrário do
    # reativar): lista as aulas e os créditos a devolver antes de confirmar —
    # foi um cancelamento acidental por seleção múltipla que nos levou a exigir
    # este passo. Também há o botão individual na ficha da sessão.
    actions = ["cancelar_sessoes", "reativar_sessoes"]
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
            path(
                "<path:object_id>/presencas/",
                self.admin_site.admin_view(self.presencas_view),
                name="bookings_session_presencas",
            ),
        ]
        return rotas + super().get_urls()

    def presencas_view(self, request, object_id):
        """
        Marca quem veio e quem faltou, a aula toda de uma vez.

        Os estados já existiam no `Booking`; o que não havia era por onde
        lhes tocar sem abrir marcação a marcação. Quem cancelou não aparece:
        cancelou a tempo, já recebeu o crédito de volta, e não é uma falta.

        **Não mexe em créditos nenhuns.** Faltar não devolve o crédito (é o
        que faz as pessoas cancelarem a tempo e libertarem a vaga) e vir
        também não cobra nada — já foi cobrado ao reservar. Por isso esta
        página não escreve no livro de movimentos: presenças não são
        dinheiro, e misturá-las com ele só daria linhas a explicar.
        """
        sessao = get_object_or_404(Session, pk=object_id)
        if not self.has_change_permission(request, sessao):
            raise PermissionDenied

        marcacoes = (
            sessao.bookings
            .exclude(status=Booking.CANCELLED)
            .select_related("client")
            .order_by("client__first_name", "client__last_name")
        )

        if request.method == "POST":
            validos = {Booking.BOOKED, Booking.ATTENDED, Booking.NO_SHOW}
            alterados = 0
            for marcacao in marcacoes:
                novo = request.POST.get(f"estado_{marcacao.pk}")
                if novo in validos and novo != marcacao.status:
                    marcacao.status = novo
                    marcacao.save(update_fields=["status"])
                    alterados += 1
            if alterados:
                messages.success(
                    request, f"Presenças guardadas ({alterados} alteradas)."
                )
            else:
                messages.info(request, "Não houve nada a alterar.")
            return redirect(
                reverse("admin:bookings_session_presencas", args=[sessao.pk])
            )

        contexto = {
            **self.admin_site.each_context(request),
            "title": f"Presenças — {sessao}",
            "sessao": sessao,
            "marcacoes": marcacoes,
            "ESTADOS": [
                (Booking.BOOKED, "Por marcar"),
                (Booking.ATTENDED, "Veio"),
                (Booking.NO_SHOW, "Faltou"),
            ],
            "opts": self.model._meta,
        }
        return render(request, "admin/bookings/session/presencas.html", contexto)

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

    @admin.action(description="Cancelar selecionadas (devolve os créditos)")
    def cancelar_sessoes(self, request, queryset):
        """
        Cancela várias aulas de uma vez, mas só depois de uma página de
        confirmação (evita o cancelamento acidental por seleção múltipla).
        Cancela via save() — nunca queryset.update(), que saltaria o
        reembolso automático dos créditos.
        """
        ativas = queryset.filter(is_cancelled=False)

        # 1º passo: sem confirmação ainda → mostrar a página de confirmação.
        if request.POST.get("confirmar") != "sim":
            total_creditos = sum(
                s.bookings.filter(status=Booking.BOOKED).count() for s in ativas
            )
            contexto = {
                **self.admin_site.each_context(request),
                "title": "Cancelar aulas selecionadas",
                "sessoes": ativas,
                "total_creditos": total_creditos,
                "action_checkbox_name": ACTION_CHECKBOX_NAME,
                "selecionadas": request.POST.getlist(ACTION_CHECKBOX_NAME),
                "opts": self.model._meta,
            }
            return render(
                request, "admin/bookings/session/cancelar_confirmacao.html", contexto
            )

        # 2º passo: confirmado → cancelar cada aula (dispara o reembolso).
        canceladas = creditos = 0
        for sessao in ativas:
            creditos += sessao.bookings.filter(status=Booking.BOOKED).count()
            sessao.is_cancelled = True
            sessao.save()
            canceladas += 1
        if canceladas:
            self.message_user(
                request,
                f"{canceladas} aula(s) cancelada(s); {creditos} crédito(s) "
                "devolvido(s) aos alunos. Não te esqueças de os avisar.",
                messages.SUCCESS,
            )
        else:
            self.message_user(
                request, "Nenhuma aula ativa na seleção.", messages.WARNING
            )
        # Devolve None → volta à lista.

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
        if obj.pk is None or obj.start is None:
            return "—"  # aula ainda por gravar (ecrã "Adicionar")
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


# NOTA: o modelo ClientPack foi apagado de todo (jul 2026). Era do desenho
# antigo, em que o saldo vivia dentro de cada pack comprado; hoje o saldo são
# os 3 saldos do utilizador (User.sessoes_sg/pt/hybrid).


@admin.register(MovimentoCredito)
class MovimentoCreditoAdmin(admin.ModelAdmin):
    """
    O extrato dos créditos: SÓ DE LEITURA, de propósito.

    Um livro que se pode editar deixa de servir para resolver discussões — é
    o mesmo princípio de um extrato bancário. Não se acrescentam, não se
    alteram e não se apagam linhas: para corrigir um saldo, o Sérgio ajusta-o
    nos Utilizadores, e esse ajuste fica aqui registado como mais uma linha.
    """

    list_display = (
        "created_at", "client", "tipo_e_quantidade", "motivo",
        "saldo_depois", "session", "feito_por",
    )
    list_filter = ("credit_type", "motivo")
    search_fields = ("client__username", "client__first_name", "client__last_name")
    date_hierarchy = "created_at"
    list_select_related = ("client", "session", "feito_por")

    @admin.display(description="Movimento", ordering="quantidade")
    def tipo_e_quantidade(self, obj):
        """Ex.: "+10 Small Group" a verde, "−1 PT" a vermelho."""
        cor = "#2e7d32" if obj.quantidade >= 0 else "#c62828"
        sinal = "+" if obj.quantidade >= 0 else "−"
        return format_html(
            '<b style="color:{}">{}{}</b> {}',
            cor, sinal, abs(obj.quantidade), obj.get_credit_type_display(),
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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
        # O nome (escolhido pelo aluno no registo) vai num atributo data- e é
        # lido em runtime com this.dataset.nome — NUNCA interpolado dentro do
        # JS do onclick. Interpolar no onclick permitia XSS: o escape de HTML
        # é desfeito pelo browser no contexto do atributo, e um nome com aspas
        # partia a string do confirm() e injetava código no painel do Sérgio.
        return format_html(
            '<a href="https://wa.me/351{}" target="_blank" rel="noopener" '
            'data-nome="{}" '
            "onclick=\"return confirm('Abrir conversa no WhatsApp com ' "
            "+ this.dataset.nome + '?')\">{}</a>",
            numero, nome, numero,
        )

    def lookup_allowed(self, lookup, value, request=None):
        # Autoriza o filtro por sessão vindo da coluna "Inscritos" da lista
        # de Sessões (o admin bloqueia lookups não declarados, por segurança).
        if lookup == "session__id__exact":
            return True
        return super().lookup_allowed(lookup, value, request)


@admin.register(WeeklyProgramSlot)
class WeeklyProgramSlotAdmin(admin.ModelAdmin):
    """
    O programa semanal do Sérgio + o botão "Gerar aulas da semana", que cria
    as sessões de uma semana a partir destes encaixes de uma só vez.
    """

    list_display = (
        "weekday", "start_time", "service_type", "location", "capacity", "active"
    )
    list_editable = ("active",)
    list_filter = ("weekday", "service_type", "active")
    ordering = ("weekday", "start_time")
    # Template com o botão "Gerar aulas da semana" no topo da lista.
    change_list_template = "admin/bookings/weeklyprogramslot/change_list.html"

    def get_urls(self):
        extra = [
            path(
                "gerar-semana/",
                self.admin_site.admin_view(self.gerar_semana_view),
                name="bookings_weeklyprogramslot_gerar",
            ),
        ]
        return extra + super().get_urls()

    @staticmethod
    def _proxima_segunda():
        """A Segunda-feira da próxima semana (default do gerador)."""
        hoje = timezone.localdate()
        return hoje + timedelta(days=(7 - hoje.weekday()))

    def gerar_semana_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied

        if request.method == "POST":
            try:
                segunda = timezone.datetime.strptime(
                    request.POST.get("segunda", ""), "%Y-%m-%d"
                ).date()
            except ValueError:
                self.message_user(
                    request, "Data inválida.", messages.ERROR
                )
                return redirect("admin:bookings_weeklyprogramslot_gerar")

            # Recuar para a Segunda dessa semana (se escolheu outro dia).
            segunda = segunda - timedelta(days=segunda.weekday())
            # Só os encaixes que o Sérgio marcou na página (por defeito, todos).
            escolhidos = request.POST.getlist("slots")
            if not escolhidos:
                self.message_user(
                    request,
                    "Não escolheste nenhuma aula para gerar.",
                    messages.WARNING,
                )
                return redirect("admin:bookings_weeklyprogramslot_gerar")

            atualizar = request.POST.get("atualizar") == "sim"
            slots = WeeklyProgramSlot.objects.filter(active=True, pk__in=escolhidos)

            criadas, atualizadas, saltadas, recusadas = [], [], [], []
            for slot in slots:
                data = segunda + timedelta(days=slot.weekday)
                ajustes = self._ajustes_do_pedido(request, slot)
                sessao, criada = slot.criar_sessao(data, **ajustes)
                etiqueta = f"{slot.get_weekday_display()} {slot.start_time:%H:%M}"

                if criada:
                    criadas.append(etiqueta)
                elif not atualizar:
                    saltadas.append(etiqueta)
                else:
                    problema = self._aplicar_ajustes(sessao, ajustes)
                    if problema:
                        recusadas.append(f"{etiqueta} — {problema}")
                    else:
                        atualizadas.append(etiqueta)

            self._relatar(request, segunda, criadas, atualizadas, saltadas, recusadas)
            return redirect("admin:bookings_session_changelist")

        # GET: página de confirmação com a data e a pré-visualização.
        contexto = {
            **self.admin_site.each_context(request),
            "title": "Gerar aulas da semana",
            "segunda": self._proxima_segunda(),
            "slots": WeeklyProgramSlot.objects.filter(active=True).select_related(
                "service_type", "location"
            ),
            # Para as caixas de seleção de cada linha.
            "tipos": ServiceType.objects.filter(active=True),
            "locais": Location.objects.filter(active=True),
            "opts": self.model._meta,
        }
        return render(
            request, "admin/bookings/weeklyprogramslot/gerar_semana.html", contexto
        )

    @staticmethod
    def _ajustes_do_pedido(request, slot):
        """
        Os valores que o Sérgio escolheu na linha deste encaixe. Só entram no
        dicionário os que ele mexeu de facto — os restantes ficam a cargo do
        `valores_por_defeito()` do encaixe.

        Valores inválidos (um id que não existe, texto na lotação) são
        ignorados em silêncio e cai-se no valor por defeito: é uma página de
        escolhas, não um formulário onde valha a pena chatear com erros.
        """
        ajustes = {}

        tipo_id = request.POST.get(f"tipo_{slot.pk}")
        if tipo_id:
            tipo = ServiceType.objects.filter(pk=tipo_id).first()
            if tipo:
                ajustes["service_type"] = tipo

        # O local é um caso especial: vazio NÃO é "não mexeu", é "online".
        # Por isso o campo só conta quando a linha vem mesmo no pedido.
        campo_local = f"local_{slot.pk}"
        if campo_local in request.POST:
            local_id = request.POST.get(campo_local)
            ajustes["location"] = (
                Location.objects.filter(pk=local_id).first() if local_id else None
            )

        lotacao = request.POST.get(f"lotacao_{slot.pk}", "").strip()
        if lotacao.isdigit() and int(lotacao) > 0:
            ajustes["capacity"] = int(lotacao)

        return ajustes

    @staticmethod
    def _aplicar_ajustes(sessao, ajustes):
        """
        Aplica os ajustes a uma aula que JÁ existe, mantendo as inscrições.

        Devolve uma frase com o motivo se a alteração for recusada, ou None se
        correu bem. As duas recusas são onde atualizar podia magoar alguém:

        - baixar a lotação abaixo dos já inscritos deixava a aula sobrelotada;
        - mudar o tipo de uma aula com gente inscrita muda o balde de créditos
          que a paga, e essas pessoas pagaram com o outro. Para isso, o
          caminho certo é cancelar a aula (que devolve os créditos, com
          confirmação e contagem) e gerar de novo.

        Nunca se apaga nada aqui: apagar a aula levaria as marcações atrás em
        cascata e desinscrevia toda a gente sem aviso.
        """
        inscritos = sessao.spots_taken

        nova_lotacao = ajustes.get("capacity")
        if nova_lotacao is not None and nova_lotacao < inscritos:
            return (
                f"já tem {inscritos} inscrito(s) e a lotação pedida era "
                f"{nova_lotacao}"
            )

        novo_tipo = ajustes.get("service_type")
        if novo_tipo and novo_tipo != sessao.service_type and inscritos:
            return (
                f"já tem {inscritos} inscrito(s) e mudar o tipo mudava os "
                "créditos que a pagam"
            )

        for campo, valor in ajustes.items():
            setattr(sessao, campo, valor)
        sessao.save(update_fields=list(ajustes) or None)
        return None

    def _relatar(self, request, segunda, criadas, atualizadas, saltadas, recusadas):
        """Diz exatamente o que aconteceu a cada aula, e não só as contagens."""
        fim = segunda + timedelta(days=6)
        cabecalho = f"Semana de {segunda:%d/%m} a {fim:%d/%m}."

        if criadas:
            self.message_user(
                request,
                f"{cabecalho} {len(criadas)} aula(s) criada(s): "
                f"{', '.join(criadas)}.",
                messages.SUCCESS,
            )
        if atualizadas:
            self.message_user(
                request,
                f"{len(atualizadas)} aula(s) já existente(s) atualizada(s), "
                f"sem mexer nas inscrições: {', '.join(atualizadas)}.",
                messages.SUCCESS,
            )
        if saltadas:
            self.message_user(
                request,
                f"{len(saltadas)} já existia(m) e ficaram como estavam: "
                f"{', '.join(saltadas)}. Para lhes aplicares os ajustes, "
                "volta a gerar com a opção de atualizar marcada.",
                messages.WARNING,
            )
        if recusadas:
            self.message_user(
                request,
                f"{len(recusadas)} não foi/foram alterada(s): "
                f"{'; '.join(recusadas)}.",
                messages.ERROR,
            )
        if not any((criadas, atualizadas, saltadas, recusadas)):
            self.message_user(request, f"{cabecalho} Nada a fazer.", messages.INFO)


def _link_whatsapp(utilizador, texto_do_confirm):
    """
    O número do aluno como link para o WhatsApp.

    O nome vai num atributo `data-` e é lido em runtime — nunca interpolado
    dentro do JS do onclick. Interpolar aí permitia XSS: o browser desfaz o
    escape de HTML no contexto do atributo, e um nome com aspas partia a
    string e injetava código no painel do Sérgio (já aconteceu uma vez, na
    coluna das Marcações).
    """
    numero = utilizador.username
    if not re.fullmatch(r"9\d{8}", numero):
        return numero
    nome = utilizador.get_full_name() or numero
    return format_html(
        '<a href="https://wa.me/351{}" target="_blank" rel="noopener" '
        'data-nome="{}" '
        "onclick=\"return confirm('{} ' + this.dataset.nome + '?')\">{}</a>",
        numero, nome, texto_do_confirm, numero,
    )


class PorAvisarFilter(admin.SimpleListFilter):
    """
    O filtro que interessa neste ecrã: quem já está inscrito e ainda não sabe.

    Fica ligado por omissão — é para isto que esta página serve. Enquanto
    tiver linhas, há gente inscrita numa aula sem saber.
    """

    title = "Por avisar"
    parameter_name = "por_avisar"

    def lookups(self, request, model_admin):
        return [("sim", "Só quem falta avisar"), ("todos", "Mostrar tudo")]

    def queryset(self, request, queryset):
        if self.value() == "todos":
            return queryset
        return queryset.por_avisar()

    def choices(self, changelist):
        """
        Deita fora o "Todos" que o Django põe sempre à frente.

        Aqui ele mentiria: esta página já começa filtrada por quem falta
        avisar, e clicar em "Todos" dava exatamente a mesma lista. Salta-se
        pela posição (é sempre o primeiro) e não pelo texto — o texto vem
        traduzido e um dia mudaria sem avisar.
        """
        return list(super().choices(changelist))[1:]


@admin.register(ListaEspera)
class ListaEsperaAdmin(admin.ModelAdmin):
    """
    Quem está à espera de vaga — e, sobretudo, quem já entrou e falta avisar.

    A app não manda mensagens a ninguém: quando abre uma vaga, o primeiro da
    fila fica inscrito e **esta lista é o aviso ao Sérgio** de que tem de lhe
    mandar uma mensagem. Clicar no número abre o WhatsApp; a seguir, marca-se
    como avisado e a linha sai daqui.
    """

    list_display = ("client", "telemovel", "session", "estado", "entrou", "avisado")
    list_filter = (PorAvisarFilter, "estado")
    search_fields = (
        "client__username", "client__first_name", "client__last_name",
    )
    actions = ("marcar_como_avisado",)
    # O aluno, a aula e as datas não se editam à mão: são o registo do que
    # aconteceu. O que se faz aqui é avisar e marcar como avisado.
    readonly_fields = ("session", "client", "estado", "created_at", "inscrito_em")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("client", "session")

    def has_add_permission(self, request):
        # Entra-se na fila pelo site, não por aqui.
        return False

    @admin.display(description="Telemóvel")
    def telemovel(self, obj):
        return _link_whatsapp(obj.client, "Avisar no WhatsApp:")

    @admin.display(description="Entrou na fila", ordering="created_at")
    def entrou(self, obj):
        return timezone.localtime(obj.created_at).strftime("%d/%m %H:%M")

    @admin.display(description="Avisado?")
    def avisado(self, obj):
        if obj.estado != ListaEspera.INSCRITO:
            return "—"
        if obj.avisado_em:
            return format_html('<span style="color:#1c7430;">✔ avisado</span>')
        return format_html(
            '<strong style="color:#ba2121;">falta avisar</strong>'
        )

    @admin.display(description="Marcar como avisado")
    def marcar_como_avisado(self, request, queryset):
        quantos = queryset.filter(
            estado=ListaEspera.INSCRITO, avisado_em__isnull=True
        ).update(avisado_em=timezone.now())
        if quantos:
            self.message_user(request, f"{quantos} aluno(s) marcados como avisados.")
        else:
            self.message_user(
                request, "Nenhum dos selecionados estava à espera de aviso."
            )
