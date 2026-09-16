from datetime import datetime, timedelta
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import SignUpForm
from .models import (
    Booking, ListaEspera, MovimentoCredito, Pack, Session,
    promover_da_lista_de_espera,
)


def _saldos_json(user):
    """Os 3 saldos como {tipo: quantidade}, para o JS atualizar os contadores."""
    return {s["tipo"]: s["quantidade"] for s in user.saldos_creditos()}


def home(request):
    """Página inicial: mostra as próximas sessões como antevisão."""
    upcoming = (
        Session.objects.filter(start__gte=timezone.now(), is_cancelled=False)
        .select_related("service_type", "location")
        .com_inscritos()
        .order_by("start")[:6]
    )
    return render(request, "home.html", {"upcoming": upcoming})


def signup(request):
    """Auto-registo de um novo aluno. Após criar a conta, entra logo."""
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Conta criada com sucesso. Bem-vindo!")
            return redirect("schedule")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def schedule(request):
    """
    Lista as sessões de um dia, com navegação para trás/frente entre dias.
    O dia vem do parâmetro ?date=AAAA-MM-DD (por defeito, hoje).
    """
    # Limites de navegação: nem sempre faz sentido andar para sempre. O aluno
    # pode ver até 3 dias atrás (aulas recentes) e 14 dias à frente (marcar).
    hoje = timezone.localdate()
    dia_min = hoje - timedelta(days=3)
    dia_max = hoje + timedelta(days=14)

    day_str = request.GET.get("date")
    try:
        day = datetime.strptime(day_str, "%Y-%m-%d").date() if day_str else hoje
    except (ValueError, TypeError):
        day = hoje
    # Não deixar sair da janela permitida (mesmo por URL escrito à mão).
    day = min(max(day, dia_min), dia_max)

    sessions = (
        Session.objects.filter(start__date=day, is_cancelled=False)
        .select_related("service_type", "location")
        .com_inscritos()
        .order_by("start")
    )
    my_session_ids = set(
        Booking.objects.filter(
            client=request.user, status=Booking.BOOKED
        ).values_list("session_id", flat=True)
    )
    # Em que filas este aluno está — um conjunto só, para o template não ter
    # de perguntar aula a aula.
    minhas_esperas = set(
        ListaEspera.objects.filter(
            client=request.user, estado=ListaEspera.A_ESPERA
        ).values_list("session_id", flat=True)
    )
    context = {
        "sessions": sessions,
        "my_session_ids": my_session_ids,
        "minhas_esperas": minhas_esperas,
        "day": day,
        "prev_day": day - timedelta(days=1),
        "next_day": day + timedelta(days=1),
        "is_today": day == hoje,
        # Para o template esconder a seta quando se chega ao limite.
        "has_prev": day > dia_min,
        "has_next": day < dia_max,
    }
    return render(request, "schedule.html", context)


@login_required
@require_POST
def book(request, session_id):
    """
    Reserva o utilizador atual numa sessão (gasta 1 crédito do tipo da aula).

    Se o pedido for AJAX (do horário, com o cabeçalho X-Requested-With),
    responde em JSON e o aluno fica na página a poder reservar mais aulas.
    Sem JS, funciona à mesma pelo caminho normal (redireciona no fim).
    """
    ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    User = get_user_model()

    with transaction.atomic():
        # select_for_update tranca a linha desta sessão até ao fim da
        # transação: dois alunos a disputar a última vaga entram em fila,
        # e o segundo já vê a vaga ocupada (em vez de ambos "ganharem").
        session = get_object_or_404(
            Session.objects.select_for_update(), pk=session_id
        )

        if session.is_cancelled or session.is_past:
            msg = "Essa sessão já não está disponível."
            if ajax:
                return JsonResponse({"ok": False, "mensagem": msg, "recarregar": True})
            messages.error(request, msg)
            return redirect("schedule")

        existing = Booking.objects.filter(
            session=session, client=request.user
        ).first()
        if existing and existing.status == Booking.BOOKED:
            if ajax:  # já inscrito: para o botão, é como sucesso (mostra Reservado)
                return JsonResponse(
                    {"ok": True, "saldos": _saldos_json(request.user),
                     "inscritos": session.spots_taken}
                )
            messages.info(request, "Já estás inscrito nesta sessão.")
            return redirect("schedule")

        if session.is_full:
            msg = "Esta sessão está esgotada."
            if ajax:
                return JsonResponse({"ok": False, "mensagem": msg, "recarregar": True})
            messages.error(request, msg)
            return redirect("schedule")

        # Desconta do balde correspondente ao tipo desta aula (SG/PT/Hybrid).
        # UPDATE condicional: só desconta se ainda houver saldo desse tipo.
        # Atómico na base de dados, por isso dois pedidos em simultâneo (duplo
        # clique, duas abas) não conseguem ambos reservar com o mesmo crédito.
        campo = User.campo_saldo(session.credit_type)
        descontou = (
            User.objects.filter(pk=request.user.pk, **{f"{campo}__gte": 1})
            .update(**{campo: F(campo) - 1})
        )
        if not descontou:
            label = session.service_type.get_credit_type_display()
            msg = (
                f"Não tens sessões de {label} disponíveis. "
                "Adquire um pacote para reservar."
            )
            if ajax:  # sem saldo: o JS leva o aluno aos pacotes
                return JsonResponse(
                    {"ok": False, "mensagem": msg, "redirect": reverse("packages")}
                )
            messages.error(request, msg)
            return redirect("packages")

        if existing:
            existing.status = Booking.BOOKED
            existing.save(update_fields=["status"])
        else:
            Booking.objects.create(
                session=session, client=request.user, status=Booking.BOOKED
            )

        # O extrato: dentro da mesma transação do desconto, para não haver
        # como ficar um sem o outro.
        MovimentoCredito.registar(
            client=request.user,
            credit_type=session.credit_type,
            quantidade=-1,
            motivo=MovimentoCredito.RESERVA,
            session=session,
            feito_por=request.user,
        )

    request.user.refresh_from_db(fields=[campo])
    restantes = request.user.creditos_de(session.credit_type)
    label = session.service_type.get_credit_type_display()
    if ajax:
        return JsonResponse(
            {
                "ok": True,
                "saldos": _saldos_json(request.user),
                "inscritos": session.spots_taken,
                "mensagem": f"Reserva feita! Ficaste com {restantes} "
                            f"sessão(ões) de {label}.",
            }
        )
    messages.success(
        request,
        f"Reserva feita! Ficaste com {restantes} sessão(ões) de {label}.",
    )
    return redirect("my_bookings")


@login_required
def my_bookings(request):
    """As reservas futuras do utilizador."""
    bookings = (
        Booking.objects.filter(
            client=request.user,
            status=Booking.BOOKED,
            session__start__gte=timezone.now(),
        )
        .select_related("session", "session__service_type", "session__location")
        .order_by("session__start")
    )
    return render(request, "my_bookings.html", {"bookings": bookings})


@login_required
@require_POST
def cancel_booking(request, booking_id):
    """Cancela uma reserva do próprio utilizador e devolve o crédito."""
    booking = get_object_or_404(Booking, pk=booking_id, client=request.user)

    can_cancel, reason = booking.client_can_cancel()
    if not can_cancel:
        messages.error(request, reason)
        return redirect("my_bookings")

    with transaction.atomic():
        # UPDATE condicional: só cancela (e devolve o crédito) se a marcação
        # ainda estiver "booked". Evita que um duplo clique devolva 2 créditos.
        cancelou = Booking.objects.filter(pk=booking.pk, status=Booking.BOOKED).update(
            status=Booking.CANCELLED
        )
        if cancelou:
            # Devolve ao balde do tipo desta aula.
            User = get_user_model()
            campo = User.campo_saldo(booking.session.credit_type)
            User.objects.filter(pk=request.user.pk).update(**{campo: F(campo) + 1})
            MovimentoCredito.registar(
                client=request.user,
                credit_type=booking.session.credit_type,
                quantidade=1,
                motivo=MovimentoCredito.CANCELAMENTO,
                session=booking.session,
                feito_por=request.user,
            )
            # A vaga que acabou de abrir vai para quem está à espera. Dentro
            # da mesma transação: ou acontecem as duas coisas, ou nenhuma.
            booking.session.refresh_from_db()
            promover_da_lista_de_espera(booking.session)

    if not cancelou:
        messages.error(request, "Esta marcação já não está ativa.")
        return redirect("my_bookings")

    messages.success(request, "Reserva cancelada. O crédito foi devolvido.")
    return redirect("my_bookings")


@login_required
def packages(request):
    """
    Mostra os pacotes disponíveis. Cada pacote tem um botão que abre o
    WhatsApp do Sérgio com uma mensagem já preenchida (a venda é tratada por
    ele diretamente).
    """
    number = settings.SERGIO_WHATSAPP
    items = []
    for pack in Pack.objects.filter(active=True).order_by("order", "name"):
        msg = pack.whatsapp_message or (
            f"Olá! Tenho interesse no pacote \"{pack.name}\" "
            f"({pack.number_of_sessions} sessões)."
        )
        items.append({"pack": pack, "wa_url": f"https://wa.me/{number}?text={quote(msg)}"})
    return render(request, "packages.html", {"items": items})


def privacidade(request):
    """
    A política de privacidade.

    Sem `login_required` de propósito: tem de se poder ler **antes** de
    decidir criar conta, senão o consentimento pedido no registo seria a
    aceitar um texto que não se podia ver.

    Os dados do responsável vêm das definições porque só o Sérgio os pode
    dar; enquanto faltarem, a página di-lo em vez de fingir que está pronta.
    """
    return render(request, "privacidade.html", {
        "responsavel": settings.RGPD_RESPONSAVEL,
        "contacto": settings.RGPD_CONTACTO,
        "prazo_anos": settings.RGPD_PRAZO_ANOS,
    })


def _voltar_ao_horario(session):
    """
    Volta ao horário **no dia da aula**, não no dia de hoje.

    O horário abre sempre em hoje. Sem isto, quem entrava na fila de uma
    aula de quinta era atirado para hoje e ficava a olhar para "não há
    sessões marcadas para este dia" — sem perceber se a ação resultou.
    """
    dia = timezone.localtime(session.start).strftime("%Y-%m-%d")
    return redirect(f"{reverse('schedule')}?date={dia}")


@login_required
@require_POST
def entrar_lista_espera(request, session_id):
    """
    Põe o aluno na fila de uma aula cheia. Não gasta créditos.

    Só faz sentido em aulas cheias: com vaga, o aluno reserva na mesma hora
    e a fila seria um passo a mais para nada.
    """
    with transaction.atomic():
        session = get_object_or_404(
            Session.objects.select_for_update(), pk=session_id
        )

        if session.is_cancelled or session.is_past:
            messages.error(request, "Essa aula já não está disponível.")
            return redirect("schedule")

        if Booking.objects.filter(
            session=session, client=request.user, status=Booking.BOOKED
        ).exists():
            messages.info(request, "Já estás inscrito nesta aula.")
            return redirect("schedule")

        if not session.is_full:
            messages.info(
                request, "Esta aula ainda tem vagas — podes reservar já."
            )
            return redirect("schedule")

        lugar, criado = ListaEspera.objects.get_or_create(
            session=session, client=request.user
        )
        if not criado and lugar.estado == ListaEspera.SAIU:
            # Voltar a entrar depois de ter saído: recomeça no fim da fila.
            lugar.estado = ListaEspera.A_ESPERA
            lugar.save(update_fields=["estado"])
            criado = True

    if criado:
        messages.success(
            request,
            "Ficaste na lista de espera. Se abrir vaga, ficas inscrito e "
            "gastas 1 sessão — o treinador avisa-te.",
        )
    else:
        messages.info(request, "Já estavas na lista de espera desta aula.")
    return _voltar_ao_horario(session)


@login_required
@require_POST
def sair_lista_espera(request, session_id):
    """Tira o aluno da fila. Não devolve nada porque nada foi gasto."""
    session = get_object_or_404(Session, pk=session_id)
    ListaEspera.objects.filter(
        session=session, client=request.user, estado=ListaEspera.A_ESPERA
    ).update(estado=ListaEspera.SAIU)
    messages.success(request, "Saíste da lista de espera.")
    return _voltar_ao_horario(session)
