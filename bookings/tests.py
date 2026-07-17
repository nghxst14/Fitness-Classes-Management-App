from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import PhoneLoginForm, SignUpForm, normalizar_telemovel
from .models import Booking, Location, ServiceType, Session

User = get_user_model()


class PhoneNormalizationTests(TestCase):
    """O mesmo número escrito de formas diferentes deve dar a mesma conta."""

    def test_normalizar_variantes(self):
        for escrito in ["912345678", "912 345 678", "912-345-678",
                        "+351912345678", "+351 912 345 678", "00351912345678"]:
            self.assertEqual(normalizar_telemovel(escrito), "912345678", escrito)

    def test_normalizar_nao_mexe_em_usernames_de_staff(self):
        self.assertEqual(normalizar_telemovel("admin"), "admin")

    def _signup_data(self, telemovel):
        return {
            "username": telemovel,
            "first_name": "Maria",
            "birth_date": "1990-05-01",
            "password1": "segredo1",
            "password2": "segredo1",
        }

    def test_registo_normaliza_o_numero(self):
        form = SignUpForm(data=self._signup_data("+351 912 345 678"))
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.username, "912345678")

    def test_registo_rejeita_numero_invalido(self):
        form = SignUpForm(data=self._signup_data("123"))
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_registo_rejeita_duplicado_com_espacos(self):
        User.objects.create_user(username="912345678", password="segredo1")
        form = SignUpForm(data=self._signup_data("912 345 678"))
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_login_aceita_numero_com_espacos(self):
        User.objects.create_user(username="912345678", password="segredo1")
        form = PhoneLoginForm(data={"username": "912 345 678", "password": "segredo1"})
        self.assertTrue(form.is_valid(), form.errors)


class SessionAdminFilterTests(TestCase):
    """Os filtros de checkbox (estado/tempo) da lista de Sessões no admin."""

    def setUp(self):
        admin_user = User.objects.create_superuser(
            username="admin-teste", password="segredo1"
        )
        self.client_http = Client()
        self.client_http.force_login(admin_user)
        service = ServiceType.objects.create(name="Aula", default_capacity=10)

        def sessao(quando, cancelada=False):
            return Session.objects.create(
                service_type=service, start=quando,
                duration_minutes=60, capacity=10, is_cancelled=cancelada,
            )

        agora = timezone.now()
        self.agendada = sessao(agora + timedelta(days=1))
        self.concluida = sessao(agora - timedelta(days=1))
        self.cancelada_futura = sessao(agora + timedelta(days=2), cancelada=True)
        self.cancelada_passada = sessao(agora - timedelta(days=2), cancelada=True)
        self.url = "/admin/bookings/session/"

    def _ids(self, params=""):
        response = self.client_http.get(self.url + params)
        return {s.pk for s in response.context["cl"].result_list}

    def test_sem_filtro_mostra_tudo(self):
        self.assertEqual(len(self._ids()), 4)

    def test_filtro_um_estado(self):
        self.assertEqual(self._ids("?estado=agendada"), {self.agendada.pk})

    def test_filtro_combina_estados(self):
        self.assertEqual(
            self._ids("?estado=agendada,cancelada"),
            {self.agendada.pk, self.cancelada_futura.pk, self.cancelada_passada.pk},
        )

    def test_estado_combinado_com_tempo(self):
        # Ex.: "canceladas passadas" — a combinação que os checkboxes permitem.
        self.assertEqual(
            self._ids("?estado=cancelada&tempo=passadas"),
            {self.cancelada_passada.pk},
        )


class SessionAdminActionTests(TestCase):
    """As ações Cancelar/Reativar da lista de Sessões no admin."""

    def setUp(self):
        admin_user = User.objects.create_superuser(
            username="admin-teste", password="segredo1"
        )
        self.client_http = Client()
        self.client_http.force_login(admin_user)
        service = ServiceType.objects.create(name="Aula", default_capacity=10)
        self.sessao = Session.objects.create(
            service_type=service, start=timezone.now() + timedelta(days=1),
            duration_minutes=60, capacity=10,
        )
        self.aluno = User.objects.create_user(
            username="912345678", password="x", credits=0
        )
        self.booking = Booking.objects.create(session=self.sessao, client=self.aluno)
        self.url = "/admin/bookings/session/"

    def _cancelar(self):
        return self.client_http.post(f"{self.url}{self.sessao.pk}/cancelar/")

    def _reativar(self):
        return self.client_http.post(f"{self.url}{self.sessao.pk}/reativar/")

    def test_botao_cancelar_devolve_creditos(self):
        self._cancelar()
        self.sessao.refresh_from_db()
        self.aluno.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertTrue(self.sessao.is_cancelled)
        self.assertEqual(self.aluno.credits, 1)
        self.assertEqual(self.booking.status, Booking.CANCELLED)

    def test_reativar_nao_inscreve_ninguem(self):
        self._cancelar()
        self._reativar()
        self.sessao.refresh_from_db()
        self.aluno.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertFalse(self.sessao.is_cancelled)
        # A marcação continua cancelada e o aluno fica com o crédito:
        # é ele que decide se se reinscreve.
        self.assertEqual(self.booking.status, Booking.CANCELLED)
        self.assertEqual(self.aluno.credits, 1)

    def test_cancelar_duas_vezes_nao_devolve_em_dobro(self):
        self._cancelar()
        self._cancelar()  # já cancelada: deve ser ignorada
        self.aluno.refresh_from_db()
        self.assertEqual(self.aluno.credits, 1)

    def test_get_nao_cancela(self):
        # Visitar o URL sem POST (ex.: pré-carregamento do browser) não
        # pode cancelar nada.
        self.client_http.get(f"{self.url}{self.sessao.pk}/cancelar/")
        self.sessao.refresh_from_db()
        self.assertFalse(self.sessao.is_cancelled)

    def test_ficha_da_sessao_nao_mostra_treinador(self):
        response = self.client_http.get(f"{self.url}{self.sessao.pk}/change/")
        self.assertNotContains(response, 'name="trainer"')

    def test_utilizadores_sem_remocao_em_massa(self):
        response = self.client_http.get("/admin/accounts/user/")
        self.assertNotContains(response, "delete_selected")

    def test_cancelar_em_massa_ja_nao_existe(self):
        # A ação em massa foi removida de propósito (cancelamento acidental
        # com seleção múltipla); garante que não volta por engano.
        response = self.client_http.post(
            self.url,
            {"action": "cancelar_sessoes", "_selected_action": [self.sessao.pk]},
        )
        self.sessao.refresh_from_db()
        self.assertFalse(self.sessao.is_cancelled)


class BookingAdminTelemovelTests(TestCase):
    """A coluna Telemóvel das Marcações liga ao WhatsApp (só números válidos)."""

    def setUp(self):
        admin_user = User.objects.create_superuser(
            username="admin-teste", password="segredo1"
        )
        self.client_http = Client()
        self.client_http.force_login(admin_user)
        service = ServiceType.objects.create(name="Aula", default_capacity=10)
        self.sessao = Session.objects.create(
            service_type=service, start=timezone.now() + timedelta(days=1),
            duration_minutes=60, capacity=10,
        )

    def test_numero_valido_tem_link_whatsapp(self):
        aluno = User.objects.create_user(username="912345678", password="x")
        Booking.objects.create(session=self.sessao, client=aluno)
        response = self.client_http.get("/admin/bookings/booking/")
        self.assertContains(response, "https://wa.me/351912345678")

    def test_username_sem_numero_nao_tem_link(self):
        aluno = User.objects.create_user(username="ManualSemNumero", password="x")
        Booking.objects.create(session=self.sessao, client=aluno)
        response = self.client_http.get("/admin/bookings/booking/")
        self.assertNotContains(response, "wa.me")


class DeleteRefundTests(TestCase):
    """Apagar (em vez de cancelar) não pode fazer desaparecer créditos."""

    def setUp(self):
        self.service = ServiceType.objects.create(name="Aula", default_capacity=10)
        self.student = User.objects.create_user(
            username="911111111", password="segredo1", credits=0
        )

    def _sessao(self, quando):
        return Session.objects.create(
            service_type=self.service,
            start=quando,
            duration_minutes=60,
            capacity=10,
        )

    def test_apagar_sessao_futura_devolve_credito(self):
        sessao = self._sessao(timezone.now() + timedelta(days=1))
        Booking.objects.create(session=sessao, client=self.student)
        sessao.delete()  # apaga a marcação em cascata
        self.student.refresh_from_db()
        self.assertEqual(self.student.credits, 1)

    def test_apagar_em_massa_no_queryset_tambem_devolve(self):
        # O admin "apagar selecionados" usa queryset.delete(), que não chama
        # o delete() de cada objeto — só os sinais. É este caminho que testamos.
        sessao = self._sessao(timezone.now() + timedelta(days=1))
        Booking.objects.create(session=sessao, client=self.student)
        Session.objects.filter(pk=sessao.pk).delete()
        self.student.refresh_from_db()
        self.assertEqual(self.student.credits, 1)

    def test_apagar_sessao_passada_nao_devolve(self):
        sessao = self._sessao(timezone.now() - timedelta(days=1))
        Booking.objects.create(session=sessao, client=self.student)
        sessao.delete()
        self.student.refresh_from_db()
        self.assertEqual(self.student.credits, 0)

    def test_apagar_marcacao_ja_cancelada_nao_devolve_outra_vez(self):
        # O cancelamento normal já devolveu o crédito; apagar depois o registo
        # não pode devolver segundo.
        sessao = self._sessao(timezone.now() + timedelta(days=1))
        booking = Booking.objects.create(
            session=sessao, client=self.student, status=Booking.CANCELLED
        )
        booking.delete()
        self.student.refresh_from_db()
        self.assertEqual(self.student.credits, 0)


class SessionCancelRefundTests(TestCase):
    """Cancelar uma sessão deve devolver o crédito e cancelar a marcação."""

    def setUp(self):
        self.service = ServiceType.objects.create(name="Aula de Grupo", default_capacity=10)
        self.location = Location.objects.create(name="Estúdio", kind=Location.INDOOR)
        self.session_obj = Session.objects.create(
            service_type=self.service,
            location=self.location,
            start=timezone.now() + timedelta(days=1),
            duration_minutes=60,
            capacity=10,
        )
        self.student = User.objects.create_user(
            username="912345678", password="segredo1", credits=0
        )
        self.booking = Booking.objects.create(
            session=self.session_obj, client=self.student, status=Booking.BOOKED
        )

    def test_cancelling_session_refunds_credit_and_cancels_booking(self):
        self.session_obj.is_cancelled = True
        self.session_obj.save()

        self.student.refresh_from_db()
        self.booking.refresh_from_db()

        self.assertEqual(self.student.credits, 1)
        self.assertEqual(self.booking.status, Booking.CANCELLED)

    def test_saving_already_cancelled_session_does_not_refund_twice(self):
        self.session_obj.is_cancelled = True
        self.session_obj.save()
        self.session_obj.save()  # segunda gravação, já estava cancelada

        self.student.refresh_from_db()
        self.assertEqual(self.student.credits, 1)


class BookViewCreditTests(TestCase):
    """A view `book` só deve reservar quando há saldo, e desconta sempre 1."""

    def setUp(self):
        self.service = ServiceType.objects.create(name="PT Individual", default_capacity=1)
        self.session_obj = Session.objects.create(
            service_type=self.service,
            start=timezone.now() + timedelta(days=1),
            duration_minutes=60,
            capacity=1,
        )
        self.student = User.objects.create_user(
            username="911111111", password="segredo1", credits=0
        )
        self.client_http = Client()
        self.client_http.force_login(self.student)

    def test_book_without_credits_redirects_to_packages(self):
        response = self.client_http.post(reverse("book", args=[self.session_obj.pk]))
        self.assertRedirects(response, reverse("packages"))
        self.assertFalse(
            Booking.objects.filter(session=self.session_obj, client=self.student).exists()
        )

    def test_book_with_credit_succeeds_and_deducts_one(self):
        self.student.credits = 1
        self.student.save(update_fields=["credits"])

        response = self.client_http.post(reverse("book", args=[self.session_obj.pk]))
        self.assertRedirects(response, reverse("my_bookings"))

        self.student.refresh_from_db()
        self.assertEqual(self.student.credits, 0)
        self.assertTrue(
            Booking.objects.filter(
                session=self.session_obj, client=self.student, status=Booking.BOOKED
            ).exists()
        )


class CancelBookingTests(TestCase):
    """Cancelar uma marcação devolve 1 crédito, mas nunca em duplicado."""

    def setUp(self):
        self.service = ServiceType.objects.create(
            name="Aula de Grupo", default_capacity=10, min_cancel_hours=0
        )
        self.session_obj = Session.objects.create(
            service_type=self.service,
            start=timezone.now() + timedelta(days=1),
            duration_minutes=60,
            capacity=10,
        )
        self.student = User.objects.create_user(
            username="922222222", password="segredo1", credits=0
        )
        self.booking = Booking.objects.create(
            session=self.session_obj, client=self.student, status=Booking.BOOKED
        )
        self.client_http = Client()
        self.client_http.force_login(self.student)

    def test_cancel_refunds_credit(self):
        self.client_http.post(reverse("cancel_booking", args=[self.booking.pk]))

        self.student.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.student.credits, 1)
        self.assertEqual(self.booking.status, Booking.CANCELLED)

    def test_cancelling_twice_only_refunds_once(self):
        self.client_http.post(reverse("cancel_booking", args=[self.booking.pk]))
        self.client_http.post(reverse("cancel_booking", args=[self.booking.pk]))

        self.student.refresh_from_db()
        self.assertEqual(self.student.credits, 1)
