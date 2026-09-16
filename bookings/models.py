from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import Count, F, Q
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


class SessionQuerySet(models.QuerySet):
    """Consultas de sessões que trazem já o que os ecrãs precisam."""

    def com_inscritos(self):
        """
        Traz o nº de inscritos de cada aula **na mesma consulta**.

        Sem isto, cada "3 / 12" no ecrã é uma ida à base de dados (uma por
        aula, o clássico N+1): dez aulas no horário eram vinte consultas, e a
        lista de Sessões do admin passava das duas centenas. Em SQLite local
        não se nota, mas em produção a base de dados está noutra máquina e
        cada ida é uma viagem pela rede.

        O resultado fica em `_inscritos`, que o `spots_taken` usa quando lá
        está. Sublinhado à frente porque é detalhe interno: quem lê o código
        continua a usar `spots_taken`.
        """
        return self.annotate(
            _inscritos=Count("bookings", filter=Q(bookings__status=Booking.BOOKED))
        )


class Session(models.Model):
    """
    Uma sessão agendada e concreta na agenda (uma aula ou um treino específico,
    num dia e hora). É a isto que os alunos se inscrevem.
    """

    objects = SessionQuerySet.as_manager()

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
        """
        Nº de vagas já ocupadas (marcações ativas).

        Se a consulta veio de `com_inscritos()`, a contagem já foi feita pela
        base de dados e é usada tal como está. Fora desse caso — um objeto
        criado à mão, um teste, o admin a gravar — conta na altura. Assim as
        páginas ficam rápidas sem obrigar ninguém a lembrar-se disto.
        """
        contados = getattr(self, "_inscritos", None)
        if contados is not None:
            return contados
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
                # Dentro da mesma transação: ou ficam os dois, ou nenhum.
                MovimentoCredito.registar(
                    client=booking.client_id,
                    credit_type=self.credit_type,
                    quantidade=1,
                    motivo=MovimentoCredito.AULA_CANCELADA,
                    session=self,
                )


class MovimentoCredito(models.Model):
    """
    O extrato dos créditos: uma linha por cada alteração de saldo.

    Porquê: o saldo no `User` é um número que se sobrescreve, e um número não
    tem memória. Quando um aluno pergunta "comprei 10, fui a 3, porque tenho
    5?", sem isto não há resposta possível — nem o histórico do admin serve,
    porque só regista que o campo mexeu (não de quanto para quanto) e não
    apanha de todo as alterações automáticas, que usam `.update()` no ORM.

    O saldo continua no `User` porque é rápido de ler (aparece no topo de
    todas as páginas). Este livro vive ao lado como a verdade auditável: se
    algum dia os dois discordarem, o livro é que manda — e a discordância é,
    ela própria, o sinal de que alguma coisa correu mal.

    **Nunca se apaga nem se edita.** No admin é só de leitura: um livro que se
    pode corrigir deixa de servir para resolver discussões.
    """

    COMPRA = "compra"
    RESERVA = "reserva"
    CANCELAMENTO = "cancelamento"
    AULA_CANCELADA = "aula_cancelada"
    MARCACAO_APAGADA = "marcacao_apagada"
    AJUSTE = "ajuste"
    MOTIVOS = [
        (COMPRA, "Créditos adicionados"),
        (RESERVA, "Reserva de aula"),
        (CANCELAMENTO, "O aluno cancelou"),
        (AULA_CANCELADA, "A aula foi cancelada"),
        (MARCACAO_APAGADA, "Marcação apagada"),
        (AJUSTE, "Ajuste manual"),
    ]

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="movimentos",
        verbose_name="Aluno",
    )
    credit_type = models.CharField(
        "Tipo de crédito", max_length=10, choices=CreditType.choices
    )
    quantidade = models.IntegerField(
        "Quantidade",
        help_text="Positivo = créditos acrescentados; negativo = gastos.",
    )
    motivo = models.CharField("Motivo", max_length=20, choices=MOTIVOS)
    saldo_depois = models.PositiveIntegerField(
        "Saldo depois",
        help_text="O saldo desse tipo logo a seguir a este movimento.",
    )
    session = models.ForeignKey(
        "Session",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="movimentos",
        verbose_name="Aula",
        help_text="A aula que originou o movimento, quando há uma.",
    )
    feito_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Feito por",
        help_text="Quem provocou o movimento. Vazio = automático.",
    )
    created_at = models.DateTimeField("Quando", auto_now_add=True)

    class Meta:
        verbose_name = "Movimento de créditos"
        verbose_name_plural = "Movimentos de créditos"
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["client", "-created_at"])]

    def __str__(self):
        sinal = "+" if self.quantidade >= 0 else ""
        return f"{self.client} {sinal}{self.quantidade} {self.get_credit_type_display()}"

    @classmethod
    def registar(cls, client, credit_type, quantidade, motivo,
                 session=None, feito_por=None):
        """
        Escreve um movimento, lendo o saldo já atualizado da base de dados.

        Chamar SEMPRE dentro da mesma transação que alterou o saldo, e DEPOIS
        de o alterar: o `saldo_depois` é lido da base de dados (e não calculado
        aqui) para o livro registar o que ficou mesmo lá, mesmo que outra coisa
        tenha mexido no saldo em simultâneo.
        """
        User = get_user_model()
        campo = User.campo_saldo(credit_type)
        saldo = (
            User.objects.filter(pk=client.pk if hasattr(client, "pk") else client)
            .values_list(campo, flat=True)
            .first()
        )
        return cls.objects.create(
            client_id=client.pk if hasattr(client, "pk") else client,
            credit_type=credit_type,
            quantidade=quantidade,
            motivo=motivo,
            saldo_depois=saldo or 0,
            session=session,
            feito_por=feito_por,
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

    def instante(self, data):
        """O início desta aula na `data` dada, em hora de Lisboa (DST-safe)."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from django.conf import settings

        return datetime.combine(data, self.start_time).replace(
            tzinfo=ZoneInfo(settings.TIME_ZONE)
        )

    def valores_por_defeito(self):
        """
        O que este encaixe usa quando nada é ajustado. Serve para pré-preencher
        a página "Gerar aulas da semana", onde o Sérgio pode mudar o tipo, o
        local e a lotação só para aquela semana — sem alterar o encaixe.
        """
        return {
            "service_type": self.service_type,
            "location": self.location,
            "capacity": self.capacity or self.service_type.default_capacity,
        }

    def criar_sessao(self, data, **ajustes):
        """
        Cria a Session desta linha na `data` dada (um datetime.date).
        Devolve (sessao, criada).

        Os `ajustes` (service_type, location, capacity) substituem os valores
        por defeito só nesta criação — o encaixe fica como está.

        Não cria se já existir uma aula NO MESMO INSTANTE, seja ela qual for.
        Antes comparava-se também o tipo de serviço, mas a partir do momento em
        que o tipo pode ser ajustado antes de gerar isso deixou de servir:
        mudar o tipo fazia o gerador não reconhecer a aula que já lá estava e
        criar uma segunda à mesma hora. O preço desta escolha é não se poderem
        ter duas aulas diferentes no mesmo instante — quando isso for preciso,
        a solução é a aula guardar de que encaixe nasceu.
        """
        inicio = self.instante(data)
        existente = Session.objects.filter(start=inicio).first()
        if existente:
            return existente, False
        valores = {**self.valores_por_defeito(), **ajustes}
        sessao = Session.objects.create(
            start=inicio,
            duration_minutes=self.duration_minutes,
            **valores,
        )
        return sessao, True


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
        # A aula pode estar a ser apagada em cascata com esta marcação: nesse
        # caso o SET_NULL do movimento trata do assunto e a linha do livro
        # fica na mesma, sem a referência à aula. O movimento não se perde.
        MovimentoCredito.registar(
            client=instance.client_id,
            credit_type=instance.session.credit_type,
            quantidade=1,
            motivo=MovimentoCredito.MARCACAO_APAGADA,
            session=instance.session,
        )
