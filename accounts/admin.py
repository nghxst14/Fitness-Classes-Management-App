from urllib.parse import quote

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import CreditType, User
from .passwords import gerar_password_provisoria
from .whatsapp import icone_whatsapp, link_whatsapp


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

    @admin.display(description="")
    def whatsapp(self, obj):
        """
        O número a abrir a conversa, na lista e na ficha.

        É na lista que o Sérgio dá os créditos; poder avisar o aluno dali
        poupa-lhe abrir a ficha só para copiar o número. Contas de staff não
        são telemóveis e aparecem sem link.

        Um ícone e não texto: a tabela tem dez colunas, e a palavra
        "conversar" gastava largura para dizer o que o símbolo diz de
        relance. O número já está na coluna do lado.
        """
        return icone_whatsapp(obj)

    @admin.display(description="Falar com o aluno")
    def whatsapp_na_ficha(self, obj):
        if not obj.pk:
            return "—"  # ecrã de criar: ainda não há número gravado
        return link_whatsapp(obj, etiqueta="Abrir conversa no WhatsApp")

    @admin.display(description="Repor a password")
    def acao_password(self, obj):
        """
        O botão de gerar uma password provisória, na secção da password.

        O `<button>` vive aqui mas pertence a um formulário que está no fim
        da página (`form="gerar-password-provisoria"`, em change_form.html).
        Tem de ser assim: tudo o que o admin desenha junto aos campos está
        dentro do formulário principal da ficha, e um <form> dentro de outro
        é descartado pelo browser sem dar erro nenhum.
        """
        if not obj.pk:
            return "—"  # ecrã de criar: ainda não há a quem mudar a password
        # Sem `onclick` com confirm(): a confirmação é uma janela nossa
        # (static/js/password-provisoria.js), que se pode escrever e desenhar.
        # Sem JavaScript isto continua a ser um submit a sério.
        return format_html(
            '<button type="submit" form="gerar-password-provisoria" '
            'class="button">Gerar password provisória</button>'
            '<p class="help" style="margin-top:.5rem;">'
            "Gera um código para lhe mandares. Ele escolhe uma nova ao "
            "entrar.</p>"
        )

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

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """
        Põe os rótulos do painel a dizer o mesmo que o site.

        O Django chama "Utilizador" ao campo de login e explica-o com
        "Obrigatório. 150 carateres ou menos. Apenas letras, dígitos
        @/./+/-/_." — regras do modelo dele, que aqui é sempre um telemóvel
        de nove dígitos. E "Primeiro nome"/"Último nome" não é como se diz
        em Portugal nem como o site lhes chama.
        """
        campo = super().formfield_for_dbfield(db_field, request, **kwargs)
        rotulos = {
            "username": ("Telemóvel", "É com este número que o aluno entra."),
            "first_name": ("Nome", ""),
            "last_name": ("Apelido", ""),
            # As três de baixo vêm traduzidas pelo Django e tratam por você
            # ("Defina se este utilizador deva ser tratado como ativo. Não
            # selecione em vez de remover as contas."), quando o resto do
            # projeto trata por tu — e a primeira nem se percebe à primeira
            # leitura.
            "is_active": (
                "Conta ativa",
                "Desmarca para suspender o acesso sem apagar a conta.",
            ),
            "is_staff": ("Acede ao painel", "Dá-lhe acesso a esta administração."),
            "is_superuser": (
                "Administrador principal",
                "Acesso total, incluindo às contas de administração.",
            ),
        }
        if db_field.name in rotulos:
            campo.label, campo.help_text = rotulos[db_field.name]
        return campo

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
            path(
                "<path:object_id>/password-provisoria/",
                self.admin_site.admin_view(self.password_provisoria_view),
                name="accounts_user_password_provisoria",
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

    def password_provisoria_view(self, request, object_id):
        """
        Gera uma password provisória e mostra-a ao treinador, uma vez.

        É a resposta ao "esqueci-me da password" que chega pelo WhatsApp.
        Substitui o formulário do Django, onde o Sérgio teria de inventar
        uma password — e onde a que ele escolhesse ficava a valer para
        sempre, se o aluno não a mudasse.

        **Só POST.** Um GET que mudasse a password de alguém era um link
        capaz de trancar uma conta por engano — bastava o browser fazer
        prefetch, ou alguém abrir o endereço por curiosidade.
        """
        aluno = get_object_or_404(User, pk=object_id)
        # A mesma regra do resto da ficha: quem não é superuser não mexe em
        # contas de administração, e uma password é a chave da porta.
        if not self.has_change_permission(request, aluno):
            raise PermissionDenied
        if request.method != "POST":
            return redirect("admin:accounts_user_change", aluno.pk)

        nova = gerar_password_provisoria()
        aluno.set_password(nova)
        aluno.deve_mudar_password = True
        aluno.save(update_fields=["password", "deve_mudar_password"])

        texto = (
            f"Olá! A tua password da app RESTART NOW foi reposta.\n\n"
            f"Telemóvel: {aluno.username}\n"
            f"Password provisória: {nova}\n\n"
            "Ao entrares, a app pede-te para escolheres uma nova."
        )
        endereco_wa = (
            f"https://wa.me/351{aluno.username}?text={quote(texto)}"
            if aluno.username.isdigit() else ""
        )

        # Com JavaScript, o painel mostra isto numa janela própria, com a
        # password numa caixa e um botão de copiar — o Sérgio pode querer
        # mandá-la por outro meio que não o WhatsApp. Sem JavaScript, segue
        # o caminho de baixo: redireciona e diz a password num aviso.
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "password": nova,
                "aluno": str(aluno),
                "whatsapp": endereco_wa,
            })

        ligacao = ""
        if endereco_wa:
            ligacao = format_html(
                ' <a href="{}" target="_blank" rel="noopener">'
                "<b>Mandar pelo WhatsApp</b></a>", endereco_wa,
            )
        # A password só aparece AQUI e AGORA: fica guardada encriptada, e
        # nem o painel a consegue voltar a mostrar.
        self.message_user(
            request,
            format_html(
                "Password provisória de {}: <code><b>{}</b></code> — "
                "anota-a agora, não volta a aparecer.{}",
                aluno, nova, ligacao,
            ),
            messages.WARNING,
        )
        return redirect("admin:accounts_user_change", aluno.pk)

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
        (None, {"fields": ("username",)}),
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
        # Sem `description`: o porquê de não haver aqui o campo do Django
        # (dizia o algoritmo, as iterações e o hash, e o link dele obrigava a
        # inventar a password à mão) é uma decisão nossa, e decisões nossas
        # vivem em comentários — não no ecrã de quem só quer usar isto.
        ("Password", {"fields": ("acao_password",)}),
        (
            "Datas",
            {
                "fields": (
                    "last_login", "date_joined", "created_at", "consentimento_em",
                ),
            },
        ),
    )
    readonly_fields = (
        "created_at", "consentimento_em", "whatsapp_na_ficha", "acao_password",
    )

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
