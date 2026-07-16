from datetime import datetime, timedelta
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import SignUpForm
from .models import Booking, Pack, Session


def home(request):
    """Página inicial: mostra as próximas sessões como antevisão."""
    upcoming = (
        Session.objects.filter(start__gte=timezone.now(), is_cancelled=False)
        .select_related("service_type", "location")
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
    day_str = request.GET.get("date")
    try:
        day = datetime.strptime(day_str, "%Y-%m-%d").date() if day_str else timezone.localdate()
    except (ValueError, TypeError):
        day = timezone.localdate()

    sessions = (
        Session.objects.filter(start__date=day, is_cancelled=False)
        .select_related("service_type", "location", "trainer")
        .order_by("start")
    )
    my_session_ids = set(
        Booking.objects.filter(
            client=request.user, status=Booking.BOOKED
        ).values_list("session_id", flat=True)
    )
    context = {
        "sessions": sessions,
        "my_session_ids": my_session_ids,
        "day": day,
        "prev_day": day - timedelta(days=1),
        "next_day": day + timedelta(days=1),
        "is_today": day == timezone.localdate(),
    }
    return render(request, "schedule.html", context)


@login_required
@require_POST
def book(request, session_id):
    """Reserva o utilizador atual numa sessão (gasta 1 crédito)."""
    session = get_object_or_404(Session, pk=session_id)

    if session.is_cancelled or session.is_past:
        messages.error(request, "Essa sessão já não está disponível.")
        return redirect("schedule")

    existing = Booking.objects.filter(session=session, client=request.user).first()
    if existing and existing.status == Booking.BOOKED:
        messages.info(request, "Já estás inscrito nesta sessão.")
        return redirect("schedule")

    if session.is_full:
        messages.error(request, "Esta sessão está esgotada.")
        return redirect("schedule")

    with transaction.atomic():
        # UPDATE condicional: só desconta o crédito se ainda houver saldo.
        # Isto é atómico na base de dados, por isso dois pedidos em simultâneo
        # (duplo clique, duas abas) não conseguem ambos ler o mesmo saldo
        # antigo e reservar os dois com um único crédito.
        descontou = (
            get_user_model()
            .objects.filter(pk=request.user.pk, credits__gte=1)
            .update(credits=F("credits") - 1)
        )
        if not descontou:
            messages.error(
                request, "Não tens créditos disponíveis. Adquire um pacote para reservar."
            )
            return redirect("packages")

        if existing:
            existing.status = Booking.BOOKED
            existing.save(update_fields=["status"])
        else:
            Booking.objects.create(
                session=session, client=request.user, status=Booking.BOOKED
            )

    request.user.refresh_from_db(fields=["credits"])
    messages.success(
        request,
        f"Reserva feita! Ficaste com {request.user.credits} crédito(s).",
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
            get_user_model().objects.filter(pk=request.user.pk).update(
                credits=F("credits") + 1
            )

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
