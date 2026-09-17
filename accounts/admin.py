from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import CreditType, User
from .whatsapp import link_whatsapp


class BirthdayTodayFilter(admin.SimpleListFilter):
    """Filtro rápido para ver quem faz anos hoje."""

    title = "Aniversário"
    parameter_name = "bday"

    def lookups(self, request, model_admin):
        return [("today", "Faz anos hoje")]

    def queryset(self, request, queryset):
        if self.value() == "today":
            today = timezone.localdate()
            return queryset.filter(
                birth_date__month=today.month, birth_date__day=today.day
            )
        return queryset


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Painel de administração dos utilizadores (login por telemóvel)."""

    class Media:
        # Bolinhas de cor por tipo de crédito nos cabeçalhos das colunas de
        # saldo (iguais às da faixa de saldos do site).
        css = {"all": ("css/admin-saldos.css",)}

    list_display = (
        "username",
        "whatsapp",
        "get_full_name",
        "sessoes_sg",
        "sessoes_pt",
        "sessoes_hybrid",
        "birth_date",
        "is_trainer",
        "is_staff",
        "historico",
    )

    @admin.display(description="WhatsApp")
    def whatsapp(self, obj):
        """
        O número a abrir a conversa, na lista e na ficha.

        É na lista que o Sérgio dá os créditos; poder avisar o aluno dali
        poupa-lhe abrir a ficha só para copiar o número. Contas de staff não
        são telemóveis e aparecem sem link.

        Mostra "conversar" e não o número: aqui ao lado, a coluna
        Utilizador já é o telemóvel.
        """
        return link_whatsapp(obj, etiqueta="conversar")

    @admin.display(description="Falar com o aluno")
    def whatsapp_na_ficha(self, obj):
        if not obj.pk:
            return "—"  # ecrã de criar: ainda não há número gravado
        return link_whatsapp(obj, etiqueta="Abrir conversa no WhatsApp")

    @admin.display(description="Histórico")
    def historico(self, obj):
        """Atalho para o extrato deste aluno, a partir da lista."""
        if obj.pk is None:
            return "—"
        url = reverse("admin:accounts_user_historico", args=[obj.pk])
        return format_html('<a href="{}">ver</a>', url)
    # Permite ao Sérgio atualizar os saldos direto na lista (após pagamento).
    list_editable = ("sessoes_sg", "sessoes_pt", "sessoes_hybrid")
    list_filter = (BirthdayTodayFilter, "is_trainer", "is_staff", "is_active")
    search_fields = ("username", "first_name", "last_name")
    ordering = ("first_name", "last_name", "username")

    def get_actions(self, request):
        # Sem remoção em massa: apagar contas é raro e delicado (histórico de
        # marcações vai atrás) — faz-se uma a uma, na ficha do utilizador,
        # como nas Sessões.
        acoes = super().get_actions(request)
        acoes.pop("delete_selected", None)
        return acoes

    def get_urls(self):
        rotas = [
            path(
                "<path:object_id>/historico/",
                self.admin_site.admin_view(self.historico_view),
                name="accounts_user_historico",
            ),
        ]
        return rotas + super().get_urls()

    def historico_view(self, request, object_id):
        """
        Tudo o que é de um aluno num sítio só: saldos, extrato e aulas.

        Serve para a pergunta que o Sérgio vai receber mais vezes — "comprei
        10, fui a 3, porque é que tenho 5?". O livro de movimentos já tinha a
        resposta desde que existe, mas espalhada por uma lista de todos os
        alunos, onde é preciso filtrar para a encontrar.
        """
        aluno = get_object_or_404(User, pk=object_id)
        if not self.has_change_permission(request, aluno):
            raise PermissionDenied

        movimentos = (
            aluno.movimentos.select_related("session", "feito_por")
            .order_by("-created_at")[:100]
        )
        marcacoes = (
            aluno.bookings.select_related("session", "session__service_type")
            .order_by("-session__start")[:50]
        )
        contexto = {
            **self.admin_site.each_context(request),
            "title": f"Histórico — {aluno}",
            "aluno": aluno,
            "saldos": aluno.saldos_creditos(),
            "movimentos": movimentos,
            "marcacoes": marcacoes,
            "opts": self.model._meta,
        }
        return render(request, "admin/accounts/user/historico.html", contexto)

    # --- Quem mexe em quem ----------------------------------------------
    # Decisão de set 2026: vai haver mais do que um administrador — o André
    # para manutenção e o Sérgio para o dia-a-dia. O Sérgio precisa de gerir
    # alunos, créditos e aulas, mas NÃO de mexer em contas de administração:
    # apagar a conta do André, ou promover alguém sem querer, são enganos
    # sem volta. Quem é superuser (o André) continua a poder tudo.
    #
    # As três portas são fechadas em conjunto de propósito: esconder o campo
    # sem proibir a ficha deixaria o caminho aberto a quem escrevesse o
    # endereço à mão.

    @staticmethod
    def _e_conta_de_admin(utilizador):
        return bool(utilizador and (utilizador.is_staff or utilizador.is_superuser))

    def get_queryset(self, request):
        """As contas de administração nem aparecem na lista ao Sérgio."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(is_staff=False, is_superuser=False)

    def has_change_permission(self, request, obj=None):
        if self._e_conta_de_admin(obj) and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if self._e_conta_de_admin(obj) and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    def get_fieldsets(self, request, obj=None):
        """
        Esconde os campos que criam administradores de quem não é superuser.

        Sem isto, o Sérgio podia dar `is_staff` a um aluno e criar um
        administrador sem dar por isso — o mesmo poder pela porta do lado.
        """
        fieldsets = super().get_fieldsets(request, obj)
        if request.user.is_superuser:
            return fieldsets

        limpos = []
        for titulo, opcoes in fieldsets:
            opcoes = dict(opcoes)
            opcoes["fields"] = tuple(
                campo for campo in opcoes.get("fields", ())
                if campo not in ("is_staff", "is_superuser")
            )
            if opcoes["fields"]:
                limpos.append((titulo, opcoes))
        return limpos

    def save_model(self, request, obj, form, change):
        """
        Regista no livro de movimentos os saldos que o Sérgio ajusta à mão.

        É por aqui que entra o dinheiro: ele recebe o pagamento pelo WhatsApp
        e soma os créditos na lista. Sem este registo, a compra — a origem de
        tudo o resto — seria a única coisa sem rasto, e o "History" do admin
        só diz que o campo mexeu, nunca de quanto para quanto.

        Serve tanto a ficha como a edição direta na lista: o admin chama o
        save_model nos dois casos, e envolve-os numa transação.
        """
        # Ler ANTES de gravar: depois já não há como saber o valor anterior.
        campos = [User.campo_saldo(t) for t, _ in CreditType.choices]
        anteriores = {}
        if change:
            anteriores = User.objects.filter(pk=obj.pk).values(*campos).first() or {}

        super().save_model(request, obj, form, change)

        if not change:
            return
        # Importado aqui e não no topo: o admin das contas não deve depender
        # da app das marcações para carregar.
        from bookings.models import MovimentoCredito

        for tipo, _ in CreditType.choices:
            campo = User.campo_saldo(tipo)
            antes, depois = anteriores.get(campo), getattr(obj, campo)
            if antes is None or antes == depois:
                continue
            MovimentoCredito.registar(
                client=obj,
                credit_type=tipo,
                quantidade=depois - antes,
                # Somar é quase sempre uma compra; tirar é uma correção.
                motivo=(MovimentoCredito.COMPRA if depois > antes
                        else MovimentoCredito.AJUSTE),
                feito_por=request.user,
            )

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Dados pessoais",
            {"fields": ("first_name", "last_name", "birth_date", "whatsapp_na_ficha")},
        ),
        (
            "Sessões disponíveis",
            {"fields": ("sessoes_sg", "sessoes_pt", "sessoes_hybrid")},
        ),
        # Sem "groups"/"user_permissions": só fariam sentido com vários
        # funcionários no admin (ver nota em bookings/admin.py).
        (
            "Permissões",
            {"fields": ("is_trainer", "is_active", "is_staff", "is_superuser")},
        ),
        (
            "Datas",
            {
                "fields": (
                    "last_login", "date_joined", "created_at", "consentimento_em",
                ),
                "description": (
                    "A data do consentimento é a prova de que o aluno aceitou "
                    "a política de privacidade no registo. É só de leitura: "
                    "uma prova que se pode escrever à mão não prova nada. "
                    "Vazia nas contas criadas aqui no painel."
                ),
            },
        ),
    )
    readonly_fields = ("created_at", "consentimento_em", "whatsapp_na_ficha")

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
    )

    @admin.display(description="Nome")
    def get_full_name(self, obj):
        return obj.get_full_name()
