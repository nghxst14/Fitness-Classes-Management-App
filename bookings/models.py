from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import F
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import CreditType


class Location(models.Model):
    """Local onde decorre a sessão (ex.: 'Estúdio', 'Parque da Cidade')."""

    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    KIND_CHOICES = [(INDOOR, "Indoor"), (OUTDOOR, "Outdoor")]

    name = models.CharField("Nome", max_length=100)
    kind = models.CharField("Tipo", max_length=10, choices=KIND_CHOICES, default=INDOOR)
    address = models.CharField("Morada / indicações", max_length=255, blank=True)
    active = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Local"
        verbose_name_plural = "Locais"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ServiceType(models.Model):
    """
    Tipo de serviço/oferta que o Sérgio vende.

    Em vez de fixarmos os tipos no código, ele cria-os no admin:
    'Aula de Grupo', 'PT Individual', 'Small Group', 'Plano Online', etc.
    Cada um traz uma lotação por defeito (1 = individual, 3 = small group...).
    """

    name = models.CharField("Nome", max_length=100)
    description = models.TextField("Descrição", blank=True)
    credit_type = models.CharField(
        "Tipo de crédito",
        max_length=10,
        choices=CreditType.choices,
        default=CreditType.SMALL_GROUP,
        help_text="Que tipo de sessões esta aula gasta. Ex.: uma aula de "
        "grupo é Small Group; um treino individual é PT.",
    )
    default_capacity = models.PositiveIntegerField(
        "Lotação por defeito",
        default=1,
        help_text="Nº de vagas sugerido para sessões deste tipo (ex.: 1 para PT, "
        "3 para small group, 12 para aula de grupo).",
    )
    is_online = models.BooleanField(
        "É online?",
        default=False,
        help_text="Marca se for um serviço à distância (sem local físico).",
    )
    min_cancel_hours = models.PositiveIntegerField(
        "Antecedência mínima para cancelar (horas)",
        default=0,
        help_text="Nº de horas antes do início até quando o aluno pode cancelar "
        "sozinho. 0 = sem restrição (ex.: aulas de grupo). Ex.: 12 para PT.",
    )
    active = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Tipo de serviço"
        verbose_name_plural = "Tipos de serviço"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Session(models.Model):
    """
    Uma sessão agendada e concreta na agenda (uma aula ou um treino específico,
    num dia e hora). É a isto que os alunos se inscrevem.
    """

    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.PROTECT,
        related_name="sessions",
        verbose_name="Tipo de serviço",
    )
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions_as_trainer",
        verbose_name="Treinador",
        limit_choices_to={"is_trainer": True},
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
        verbose_name="Local",
        help_text="Deixar vazio se for uma sessão online.",
    )
    title = models.CharField(
        "Título (opcional)",
        max_length=120,
        blank=True,
        help_text="Se vazio, usa-se o nome do tipo de serviço.",
    )
    start = models.DateTimeField("Início")
    duration_minutes = models.PositiveIntegerField("Duração (minutos)", default=60)
    capacity = models.PositiveIntegerField(
        "Lotação (nº de vagas)",
        help_text="Nº máximo de alunos nesta sessão.",
    )
    is_cancelled = models.BooleanField("Cancelada", default=False)
    notes = models.TextField("Notas", blank=True)
    created_at = models.DateTimeField("Criada em", auto_now_add=True)

    class Meta:
        verbose_name = "Sessão"
        verbose_name_plural = "Sessões"
        ordering = ["start"]

    def __str__(self):
        label = self.title or self.service_type.name
        return f"{label} — {timezone.localtime(self.start):%d/%m/%Y %H:%M}"

    @property
    def end(self):
        """Hora de fim, calculada a partir do início + duração."""
        return self.start + timedelta(minutes=self.duration_minutes)

    @property
    def spots_taken(self):
        """Nº de vagas já ocupadas (marcações ativas)."""
        return self.bookings.filter(status=Booking.BOOKED).count()

    @property
    def spots_left(self):
        """Vagas ainda disponíveis."""
        return max(self.capacity - self.spots_taken, 0)

    @property
    def is_full(self):
        return self.spots_left <= 0

    @property
    def is_past(self):
        return self.start < timezone.now()

    @property
    def credit_type(self):
        """O tipo de crédito que reservar esta aula gasta (vem do serviço)."""
        return self.service_type.credit_type

    @property
    def card_image(self):
        """
        Imagem de fundo do cartão: outdoor/indoor conforme o local; se não há
        local, é uma sessão online e usa a imagem própria.
        """
        if self.location and self.location.kind == Location.OUTDOOR:
            return "img/brand/class-outdoor.jpg"
        if self.location and self.location.kind == Location.INDOOR:
            return "img/brand/class-indoor.jpg"
        return "img/brand/class-online.jpg"

    def save(self, *args, **kwargs):
        """
        Deteta quando a sessão passa a cancelada (is_cancelled: False -> True)
        e, nesse caso, cancela as marcações ativas e devolve o crédito a cada
        aluno. Sem isto, um aluno perdia o crédito por uma aula cancelada pelo
        próprio treinador (ex.: chuva numa aula outdoor).
        """
        was_cancelled = None
        if self.pk:
            was_cancelled = (
                Session.objects.filter(pk=self.pk)
                .values_list("is_cancelled", flat=True)
                .first()
            )
        super().save(*args, **kwargs)
        if self.is_cancelled and was_cancelled is False:
            self._refund_active_bookings()

    def _refund_active_bookings(self):
        User = get_user_model()
        campo = User.campo_saldo(self.credit_type)  # balde certo desta aula
        with transaction.atomic():
            for booking in self.bookings.filter(status=Booking.BOOKED):
                booking.status = Booking.CANCELLED
                booking.save(update_fields=["status"])
                User.objects.filter(pk=booking.client_id).update(
                    **{campo: F(campo) + 1}
                )


class Pack(models.Model):
    """
    Um produto de pack de sessões que o aluno pode comprar
    (ex.: 'Pack 10 sessões PT', válido 60 dias).
    """

    name = models.CharField("Nome", max_length=100)
    description = models.CharField(
        "Descrição curta", max_length=200, blank=True,
        help_text="Aparece no cartão do pacote no site.",
    )
    credit_type = models.CharField(
        "Tipo de crédito",
        max_length=10,
        choices=CreditType.choices,
        default=CreditType.SMALL_GROUP,
        help_text="Que tipo de sessões este pacote dá ao aluno.",
    )
    number_of_sessions = models.PositiveIntegerField("Nº de sessões (créditos)")
    price = models.DecimalField(
        "Preço (€)", max_digits=7, decimal_places=2, null=True, blank=True
    )
    whatsapp_message = models.TextField(
        "Mensagem de WhatsApp",
        blank=True,
        help_text="Mensagem já preenchida quando o aluno clica no pacote. "
        "Se vazio, é usada uma mensagem genérica.",
    )
    order = models.PositiveIntegerField("Ordem", default=0)
    active = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Pacote"
        verbose_name_plural = "Pacotes"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.number_of_sessions} sessões)"


class WeeklyProgramSlot(models.Model):
    """
    Um encaixe fixo do programa semanal do Sérgio (ex.: "toda a 2ª às 08:00").

    É o "molde" a partir do qual se geram as sessões de uma semana com um
    clique. O que é fixo é o **horário**; o tipo de serviço e o local aqui são
    apenas o valor por defeito (o Sérgio ajusta as sessões geradas de cada
    semana, que variam). Ver o admin: ação "Gerar aulas da semana".
    """

    WEEKDAYS = [
        (0, "Segunda"), (1, "Terça"), (2, "Quarta"), (3, "Quinta"),
        (4, "Sexta"), (5, "Sábado"), (6, "Domingo"),
    ]

    weekday = models.IntegerField("Dia da semana", choices=WEEKDAYS)
    start_time = models.TimeField("Hora de início")
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.PROTECT,
        related_name="program_slots",
        verbose_name="Tipo de serviço (por defeito)",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="program_slots",
        verbose_name="Local (por defeito)",
        help_text="Vazio = sessão online.",
    )
    capacity = models.PositiveIntegerField(
        "Lotação",
        null=True,
        blank=True,
        help_text="Vazio usa a lotação por defeito do tipo de serviço.",
    )
    duration_minutes = models.PositiveIntegerField("Duração (minutos)", default=60)
    active = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Aula recorrente (programa semanal)"
        verbose_name_plural = "Programa semanal"
        ordering = ["weekday", "start_time"]

    def __str__(self):
        return f"{self.get_weekday_display()} {self.start_time:%H:%M} — {self.service_type.name}"

    def criar_sessao(self, data):
        """
        Cria a Session desta linha na `data` dada (um datetime.date), em hora
        de Lisboa. Devolve (sessao, criada). Não cria se já existir uma sessão
        no mesmo instante e tipo — assim clicar "gerar" duas vezes não duplica.
        """
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from django.conf import settings

        inicio = datetime.combine(data, self.start_time).replace(
            tzinfo=ZoneInfo(settings.TIME_ZONE)
        )
        ja_existe = Session.objects.filter(
            start=inicio, service_type=self.service_type
        ).exists()
        if ja_existe:
            return None, False
        sessao = Session.objects.create(
            service_type=self.service_type,
            location=self.location,
            start=inicio,
            duration_minutes=self.duration_minutes,
            capacity=self.capacity or self.service_type.default_capacity,
        )
        return sessao, True


class ClientPack(models.Model):
    """
    Um pack efetivamente comprado por um aluno.

    Guardamos o total e as sessões usadas (em vez de ligar diretamente ao Pack)
    para que o histórico não mude se o Sérgio editar o produto Pack mais tarde.
    A lógica de descontar sessões ao marcar fica para o Bloco 2.
    """

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="packs",
        verbose_name="Aluno",
    )
    pack = models.ForeignKey(
        Pack,
        on_delete=models.SET_NULL,
        null=True,
        related_name="purchases",
        verbose_name="Pack",
    )
    sessions_total = models.PositiveIntegerField("Sessões (total)")
    sessions_used = models.PositiveIntegerField("Sessões usadas", default=0)
    purchased_at = models.DateField("Comprado em", default=timezone.now)
    expires_at = models.DateField("Expira em", null=True, blank=True)
    note = models.CharField("Nota", max_length=255, blank=True)

    class Meta:
        verbose_name = "Pack do aluno"
        verbose_name_plural = "Packs dos alunos"
        ordering = ["-purchased_at"]

    def __str__(self):
        who = self.client.get_full_name() or self.client.username
        return f"{who} — {self.sessions_remaining}/{self.sessions_total} sessões"

    @property
    def sessions_remaining(self):
        return max(self.sessions_total - self.sessions_used, 0)

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at < timezone.localdate())

    @property
    def is_usable(self):
        """Ainda tem sessões e não expirou."""
        return self.sessions_remaining > 0 and not self.is_expired


class Booking(models.Model):
    """Uma marcação: um aluno inscrito numa sessão."""

    BOOKED = "booked"
    CANCELLED = "cancelled"
    ATTENDED = "attended"
    NO_SHOW = "no_show"
    STATUS_CHOICES = [
        (BOOKED, "Marcada"),
        (CANCELLED, "Cancelada"),
        (ATTENDED, "Compareceu"),
        (NO_SHOW, "Faltou"),
    ]

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="bookings",
        verbose_name="Sessão",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        verbose_name="Aluno",
    )
    status = models.CharField(
        "Estado", max_length=10, choices=STATUS_CHOICES, default=BOOKED
    )
    client_pack = models.ForeignKey(
        ClientPack,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
        verbose_name="Pack usado",
        help_text="Pack de onde saiu esta sessão (se aplicável).",
    )
    created_at = models.DateTimeField("Criada em", auto_now_add=True)

    class Meta:
        verbose_name = "Marcação"
        verbose_name_plural = "Marcações"
        ordering = ["-created_at"]
        # Impede o mesmo aluno de marcar duas vezes a mesma sessão.
        constraints = [
            models.UniqueConstraint(
                fields=["session", "client"], name="unique_booking_por_sessao"
            )
        ]

    def __str__(self):
        who = self.client.get_full_name() or self.client.username
        return f"{who} → {self.session}"

    def client_can_cancel(self):
        """
        Diz se o próprio aluno pode cancelar esta marcação, e uma razão
        caso não possa. O Sérgio (admin) cancela sempre pelo painel.

        Regra: a antecedência mínima vem do tipo de serviço
        (min_cancel_hours). 0 = sem restrição.
        """
        if self.status != self.BOOKED:
            return False, "Esta marcação já não está ativa."
        if self.session.is_cancelled:
            return False, "Esta sessão foi cancelada."
        if self.session.is_past:
            return False, "Esta sessão já passou."

        min_hours = self.session.service_type.min_cancel_hours
        if min_hours > 0:
            limit = self.session.start - timedelta(hours=min_hours)
            if timezone.now() > limit:
                return (
                    False,
                    f"Só é possível cancelar até {min_hours}h antes do início. "
                    "Para casos excecionais, fala com o teu treinador.",
                )
        return True, ""

    @property
    def client_cancellable(self):
        """Versão booleana simples (útil nos templates)."""
        can, _ = self.client_can_cancel()
        return can


@receiver(pre_delete, sender=Booking)
def devolver_credito_ao_apagar_marcacao(sender, instance, **kwargs):
    """
    Se uma marcação ativa de uma sessão futura for APAGADA (e não cancelada),
    devolve o crédito ao aluno.

    Porquê um sinal e não Booking.delete()? Porque quando o Sérgio apaga uma
    Sessão no admin, as marcações vão atrás em cascata — e nesse caminho o
    Django não chama o delete() de cada marcação, mas dispara sempre este
    sinal. Sem isto, apagar uma sessão (em vez de a cancelar) fazia os
    créditos dos alunos desaparecerem silenciosamente.

    Sessões passadas não devolvem crédito: a aula já aconteceu.
    """
    if (
        instance.status == Booking.BOOKED
        and not instance.session.is_past
        and not instance.session.is_cancelled
    ):
        User = get_user_model()
        campo = User.campo_saldo(instance.session.credit_type)
        User.objects.filter(pk=instance.client_id).update(
            **{campo: F(campo) + 1}
        )
