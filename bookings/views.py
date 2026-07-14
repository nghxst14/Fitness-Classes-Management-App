from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import SignUpForm
from .models import Booking, Session


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
    """Lista as sessões futuras disponíveis para marcar."""
    sessions = (
        Session.objects.filter(start__gte=timezone.now(), is_cancelled=False)
        .select_related("service_type", "location")
        .order_by("start")
    )
    # IDs das sessões em que o utilizador já está inscrito (para mudar o botão).
    my_session_ids = set(
        Booking.objects.filter(
            client=request.user, status=Booking.BOOKED
        ).values_list("session_id", flat=True)
    )
    return render(
        request,
        "schedule.html",
        {"sessions": sessions, "my_session_ids": my_session_ids},
    )


@login_required
@require_POST
def book(request, session_id):
    """Marca o utilizador atual numa sessão (com validações)."""
    session = get_object_or_404(Session, pk=session_id)

    if session.is_cancelled or session.is_past:
        messages.error(request, "Essa sessão já não está disponível.")
        return redirect("schedule")

    # Reaproveita uma marcação anterior cancelada, se existir
    # (evita conflito com a restrição de unicidade sessão+aluno).
    booking, created = Booking.objects.get_or_create(
        session=session,
        client=request.user,
        defaults={"status": Booking.BOOKED},
    )

    if not created and booking.status == Booking.BOOKED:
        messages.info(request, "Já estás inscrito nesta sessão.")
        return redirect("schedule")

    # Verifica lotação (conta as marcações ativas no momento).
    if session.is_full:
        messages.error(request, "Esta sessão está esgotada.")
        return redirect("schedule")

    booking.status = Booking.BOOKED
    try:
        booking.save()
    except IntegrityError:
        messages.error(request, "Não foi possível concluir a marcação.")
        return redirect("schedule")

    messages.success(request, "Marcação feita com sucesso!")
    return redirect("my_bookings")


@login_required
def my_bookings(request):
    """As marcações futuras do utilizador."""
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
    """Cancela uma marcação do próprio utilizador, respeitando a regra."""
    booking = get_object_or_404(Booking, pk=booking_id, client=request.user)

    can_cancel, reason = booking.client_can_cancel()
    if not can_cancel:
        messages.error(request, reason)
        return redirect("my_bookings")

    booking.status = Booking.CANCELLED
    booking.save()
    messages.success(request, "Marcação cancelada.")
    return redirect("my_bookings")
