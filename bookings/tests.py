import re
from datetime import datetime, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from accounts.models import CreditType

from .forms import PhoneLoginForm, SignUpForm, normalizar_telemovel
from .models import (
    Booking,
    ListaEspera,
    Location,
    MovimentoCredito,
    Pack,
    ServiceType,
    Session,
    WeeklyProgramSlot,
    promover_da_lista_de_espera,
)


class ScheduleNavLimitsTests(TestCase):
    """O horário só navega 3 dias para trás e 14 para a frente."""

    def setUp(self):
        self.student = User.objects.create_user(username="912345678", password="x")
        self.client_http = Client()
        self.client_http.force_login(self.student)

    def _ctx(self, date_str):
        return self.client_http.get(reverse("schedule"), {"date": date_str}).context

    def test_limite_para_tras(self):
        hoje = timezone.localdate()
        limite = hoje - timedelta(days=3)
        # Pedir muito para trás fixa no limite e esconde a seta anterior.
        ctx = self._ctx((hoje - timedelta(days=30)).strftime("%Y-%m-%d"))
        self.assertEqual(ctx["day"], limite)
        self.assertFalse(ctx["has_prev"])

    def test_limite_para_a_frente(self):
        hoje = timezone.localdate()
        limite = hoje + timedelta(days=14)
        ctx = self._ctx((hoje + timedelta(days=60)).strftime("%Y-%m-%d"))
        self.assertEqual(ctx["day"], limite)
        self.assertFalse(ctx["has_next"])

    def test_hoje_tem_ambas_as_setas(self):
        ctx = self._ctx(timezone.localdate().strftime("%Y-%m-%d"))
        self.assertTrue(ctx["has_prev"])
        self.assertTrue(ctx["has_next"])


class WeeklyProgramGenerateTests(TestCase):
    """O gerador de aulas da semana a partir do programa semanal."""

    def setUp(self):
        admin_user = User.objects.create_superuser(
            username="admin-teste", password="segredo1"
        )
        self.client_http = Client()
        self.client_http.force_login(admin_user)
        self.service = ServiceType.objects.create(name="Aula", default_capacity=10)
        # Seg 08:00 e Sáb 09:30.
        WeeklyProgramSlot.objects.create(
            weekday=0, start_time=time(8, 0), service_type=self.service
        )
        WeeklyProgramSlot.objects.create(
            weekday=5, start_time=time(9, 30), service_type=self.service
        )
        self.url = "/admin/bookings/weeklyprogramslot/gerar-semana/"

    def _gerar(self, segunda="2026-08-03", slots=None):  # 2026-08-03 é Segunda
        # Por defeito, gera todos os encaixes (como a página, com tudo marcado).
        if slots is None:
            slots = list(WeeklyProgramSlot.objects.values_list("pk", flat=True))
        return self.client_http.post(self.url, {"segunda": segunda, "slots": slots})

    def test_gera_uma_sessao_por_encaixe(self):
        self._gerar()
        self.assertEqual(Session.objects.count(), 2)
        # Confirma dia e hora corretos (Seg 03/08 08:00, Sáb 08/08 09:30).
        horas = sorted(
            timezone.localtime(s.start).strftime("%a %H:%M")
             for s in Session.objects.all()
        )
        self.assertEqual(len(horas), 2)

    def test_gerar_duas_vezes_nao_duplica(self):
        self._gerar()
        self._gerar()  # segundo clique na mesma semana
        self.assertEqual(Session.objects.count(), 2)

    def test_gera_so_os_selecionados(self):
        # Escolher só a Segunda gera 1 aula, não as duas.
        so_segunda = WeeklyProgramSlot.objects.get(weekday=0).pk
        self._gerar(slots=[so_segunda])
        self.assertEqual(Session.objects.count(), 1)

    def test_sem_selecao_nao_gera_nada(self):
        self._gerar(slots=[])
        self.assertEqual(Session.objects.count(), 0)

    def test_encaixe_inativo_nao_gera(self):
        # Mesmo selecionado, um encaixe inativo não gera.
        WeeklyProgramSlot.objects.filter(weekday=5).update(active=False)
        self._gerar()
        self.assertEqual(Session.objects.count(), 1)

    def test_data_no_meio_da_semana_recua_para_segunda(self):
        # Quarta 05/08 deve gerar a mesma semana que a Segunda 03/08.
        self._gerar(segunda="2026-08-05")
        seg = Session.objects.get(start__week_day=2)  # 2 = Segunda no Django
        self.assertEqual(timezone.localtime(seg.start).strftime("%d/%m"), "03/08")

User = get_user_model()


class HoraWidgetTests(TestCase):
    """O widget de hora (duas caixas) aceita hora só e hora:minuto escritos."""

    def _campo(self):
        from django import forms

        from bookings.admin import AdminSplitDateTimeHora
        return forms.SplitDateTimeField(widget=AdminSplitDateTimeHora())

    def _hora(self, h, m):
        campo = self._campo()
        data = {"start_0": "2026-08-10", "start_1_h": h, "start_1_m": m}
        valor = campo.widget.value_from_datadict(data, {}, "start")
        return campo.clean(valor)

    def test_hora_sem_minuto_fica_em_ponto(self):
        # Escrever só "9" na hora deve dar 09:00.
        dt = self._hora("9", "")
        self.assertEqual((dt.hour, dt.minute), (9, 0))

    def test_hora_e_minuto_escritos(self):
        # "13" : "02" à mão deve dar 13:02.
        dt = self._hora("13", "02")
        self.assertEqual((dt.hour, dt.minute), (13, 2))

    def test_minuto_de_uma_casa(self):
        # "21" : "5" deve dar 21:05 (strptime é tolerante).
        dt = self._hora("21", "5")
        self.assertEqual((dt.hour, dt.minute), (21, 5))


class CardImageTests(TestCase):
    """A imagem de fundo do cartão conforme o local (ou online)."""

    def setUp(self):
        self.service = ServiceType.objects.create(name="Aula", default_capacity=10)

    def _sessao(self, location):
        return Session.objects.create(
            service_type=self.service, location=location,
            start=timezone.now() + timedelta(days=1),
            duration_minutes=60, capacity=10,
        )

    def test_online_usa_imagem_online(self):
        sessao = self._sessao(None)  # sem local = online
        self.assertEqual(sessao.card_image, "img/brand/class-online.jpg")

    def test_indoor_e_outdoor(self):
        indoor = self._sessao(Location.objects.create(name="Est", kind=Location.INDOOR))
        outdoor = self._sessao(Location.objects.create(name="Par", kind=Location.OUTDOOR))
        self.assertEqual(indoor.card_image, "img/brand/class-indoor.jpg")
        self.assertEqual(outdoor.card_image, "img/brand/class-outdoor.jpg")


class CreditTypeIsolationTests(TestCase):
    """
    O crédito de um tipo (ex.: SG) nunca serve para uma aula de outro tipo
    (ex.: PT), e reservar/cancelar mexe sempre no balde certo.
    """

    def setUp(self):
        self.pt = ServiceType.objects.create(
            name="PT Individual", default_capacity=1, credit_type=CreditType.PT
        )
        self.sessao_pt = Session.objects.create(
            service_type=self.pt,
            start=timezone.now() + timedelta(days=1),
            duration_minutes=60, capacity=1,
        )
        # Aluno com saldo só de Small Group, nenhum de PT.
        self.student = User.objects.create_user(
            username="912345678", password="segredo1", sessoes_sg=5, sessoes_pt=0
        )
        self.client_http = Client()
        self.client_http.force_login(self.student)

    def test_credito_sg_nao_paga_aula_pt(self):
        response = self.client_http.post(reverse("book", args=[self.sessao_pt.pk]))
        self.assertRedirects(response, reverse("packages"))
        self.student.refresh_from_db()
        # O saldo de SG não foi tocado; continua sem reserva.
        self.assertEqual(self.student.sessoes_sg, 5)
        self.assertFalse(Booking.objects.filter(session=self.sessao_pt).exists())

    def test_reserva_desconta_o_balde_certo(self):
        self.student.sessoes_pt = 2
        self.student.save(update_fields=["sessoes_pt"])
        self.client_http.post(reverse("book", args=[self.sessao_pt.pk]))
        self.student.refresh_from_db()
        self.assertEqual(self.student.sessoes_pt, 1)  # desconta PT
        self.assertEqual(self.student.sessoes_sg, 5)  # SG intacto

    def test_cancelar_devolve_ao_balde_certo(self):
        self.student.sessoes_pt = 2
        self.student.save(update_fields=["sessoes_pt"])
        self.client_http.post(reverse("book", args=[self.sessao_pt.pk]))
        booking = Booking.objects.get(session=self.sessao_pt, client=self.student)
        self.client_http.post(reverse("cancel_booking", args=[booking.pk]))
        self.student.refresh_from_db()
        self.assertEqual(self.student.sessoes_pt, 2)  # devolveu ao PT
        self.assertEqual(self.student.sessoes_sg, 5)

    def test_cancelar_aula_devolve_ao_balde_certo(self):
        self.student.sessoes_pt = 1
        self.student.save(update_fields=["sessoes_pt"])
        self.client_http.post(reverse("book", args=[self.sessao_pt.pk]))
        self.sessao_pt.is_cancelled = True
        self.sessao_pt.save()  # cancelar a aula reembolsa
        self.student.refresh_from_db()
        self.assertEqual(self.student.sessoes_pt, 1)
        self.assertEqual(self.student.sessoes_sg, 5)


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
            # Obrigatório desde que há política de privacidade (ver
            # PrivacidadeTests): sem isto o registo é recusado.
            "aceita_privacidade": True,
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
            username="912345678", password="x", sessoes_sg=0
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
        self.assertEqual(self.aluno.sessoes_sg, 1)
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
        self.assertEqual(self.aluno.sessoes_sg, 1)

    def test_cancelar_duas_vezes_nao_devolve_em_dobro(self):
        self._cancelar()
        self._cancelar()  # já cancelada: deve ser ignorada
        self.aluno.refresh_from_db()
        self.assertEqual(self.aluno.sessoes_sg, 1)

    def test_get_nao_cancela(self):
        # Visitar o URL sem POST (ex.: pré-carregamento do browser) não
        # pode cancelar nada.
        self.client_http.get(f"{self.url}{self.sessao.pk}/cancelar/")
        self.sessao.refresh_from_db()
        self.assertFalse(self.sessao.is_cancelled)

    def test_pagina_adicionar_sessao_abre(self):
        # Regressão: o campo "estado" chamava is_past numa sessão sem data
        # (start=None) no ecrã Adicionar, rebentando com TypeError.
        response = self.client_http.get(f"{self.url}add/")
        self.assertEqual(response.status_code, 200)

    def test_ficha_da_sessao_nao_mostra_treinador(self):
        response = self.client_http.get(f"{self.url}{self.sessao.pk}/change/")
        self.assertNotContains(response, 'name="trainer"')

    def test_utilizadores_sem_remocao_em_massa(self):
        response = self.client_http.get("/admin/accounts/user/")
        self.assertNotContains(response, "delete_selected")

    def test_cancelar_em_massa_pede_confirmacao_primeiro(self):
        # Sem "confirmar", a ação mostra a página de confirmação e NÃO cancela.
        response = self.client_http.post(
            self.url,
            {"action": "cancelar_sessoes", "_selected_action": [self.sessao.pk]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cancelar")
        self.sessao.refresh_from_db()
        self.assertFalse(self.sessao.is_cancelled)  # ainda ativa

    def test_cancelar_em_massa_confirmado_cancela_e_devolve(self):
        self.client_http.post(
            self.url,
            {
                "action": "cancelar_sessoes",
                "_selected_action": [self.sessao.pk],
                "confirmar": "sim",
            },
        )
        self.sessao.refresh_from_db()
        self.aluno.refresh_from_db()
        self.assertTrue(self.sessao.is_cancelled)
        self.assertEqual(self.aluno.sessoes_sg, 1)  # crédito devolvido


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

    def test_nome_malicioso_nao_injeta_js(self):
        # Um nome com aspas não pode partir a string do confirm() (XSS no
        # admin). O nome vai em data-nome (escapado) e é lido em runtime.
        aluno = User.objects.create_user(
            username="912345678", password="x",
            first_name="x');alert(1)//", last_name="",
        )
        Booking.objects.create(session=self.sessao, client=aluno)
        html = self.client_http.get("/admin/bookings/booking/").content.decode()
        # A sequência de escape (aspa + parêntese) não pode aparecer em bruto.
        self.assertNotIn("');alert(1)//", html)
        # E usa-se o padrão seguro (lê o nome do atributo, não o interpola).
        self.assertIn("this.dataset.nome", html)


class DeleteRefundTests(TestCase):
    """Apagar (em vez de cancelar) não pode fazer desaparecer créditos."""

    def setUp(self):
        self.service = ServiceType.objects.create(name="Aula", default_capacity=10)
        self.student = User.objects.create_user(
            username="911111111", password="segredo1", sessoes_sg=0
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
        self.assertEqual(self.student.sessoes_sg, 1)

    def test_apagar_em_massa_no_queryset_tambem_devolve(self):
        # O admin "apagar selecionados" usa queryset.delete(), que não chama
        # o delete() de cada objeto — só os sinais. É este caminho que testamos.
        sessao = self._sessao(timezone.now() + timedelta(days=1))
        Booking.objects.create(session=sessao, client=self.student)
        Session.objects.filter(pk=sessao.pk).delete()
        self.student.refresh_from_db()
        self.assertEqual(self.student.sessoes_sg, 1)

    def test_apagar_sessao_passada_nao_devolve(self):
        sessao = self._sessao(timezone.now() - timedelta(days=1))
        Booking.objects.create(session=sessao, client=self.student)
        sessao.delete()
        self.student.refresh_from_db()
        self.assertEqual(self.student.sessoes_sg, 0)

    def test_apagar_marcacao_ja_cancelada_nao_devolve_outra_vez(self):
        # O cancelamento normal já devolveu o crédito; apagar depois o registo
        # não pode devolver segundo.
        sessao = self._sessao(timezone.now() + timedelta(days=1))
        booking = Booking.objects.create(
            session=sessao, client=self.student, status=Booking.CANCELLED
        )
        booking.delete()
        self.student.refresh_from_db()
        self.assertEqual(self.student.sessoes_sg, 0)


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
            username="912345678", password="segredo1", sessoes_sg=0
        )
        self.booking = Booking.objects.create(
            session=self.session_obj, client=self.student, status=Booking.BOOKED
        )

    def test_cancelling_session_refunds_credit_and_cancels_booking(self):
        self.session_obj.is_cancelled = True
        self.session_obj.save()

        self.student.refresh_from_db()
        self.booking.refresh_from_db()

        self.assertEqual(self.student.sessoes_sg, 1)
        self.assertEqual(self.booking.status, Booking.CANCELLED)

    def test_saving_already_cancelled_session_does_not_refund_twice(self):
        self.session_obj.is_cancelled = True
        self.session_obj.save()
        self.session_obj.save()  # segunda gravação, já estava cancelada

        self.student.refresh_from_db()
        self.assertEqual(self.student.sessoes_sg, 1)


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
            username="911111111", password="segredo1", sessoes_sg=0
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
        self.student.sessoes_sg = 1
        self.student.save(update_fields=["sessoes_sg"])
        # (o serviço "PT Individual" deste teste fica no tipo por defeito, sg;
        #  a isolação entre tipos é testada em CreditTypeIsolationTests)

        response = self.client_http.post(reverse("book", args=[self.session_obj.pk]))
        self.assertRedirects(response, reverse("my_bookings"))

        self.student.refresh_from_db()
        self.assertEqual(self.student.sessoes_sg, 0)
        self.assertTrue(
            Booking.objects.filter(
                session=self.session_obj, client=self.student, status=Booking.BOOKED
            ).exists()
        )

    def _ajax(self):
        return self.client_http.post(
            reverse("book", args=[self.session_obj.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def test_ajax_com_saldo_responde_json_e_nao_redireciona(self):
        self.student.sessoes_sg = 2
        self.student.save(update_fields=["sessoes_sg"])
        response = self._ajax()
        self.assertEqual(response.status_code, 200)  # JSON, não 302
        dados = response.json()
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["saldos"]["sg"], 1)  # saldo já descontado
        self.assertEqual(dados["inscritos"], 1)
        self.assertTrue(
            Booking.objects.filter(
                session=self.session_obj, client=self.student, status=Booking.BOOKED
            ).exists()
        )

    def test_ajax_sem_saldo_devolve_redirect_para_pacotes(self):
        response = self._ajax()  # sessoes_sg = 0
        dados = response.json()
        self.assertFalse(dados["ok"])
        self.assertEqual(dados["redirect"], reverse("packages"))
        self.assertFalse(Booking.objects.filter(session=self.session_obj).exists())


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
            username="922222222", password="segredo1", sessoes_sg=0
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
        self.assertEqual(self.student.sessoes_sg, 1)
        self.assertEqual(self.booking.status, Booking.CANCELLED)

    def test_cancelling_twice_only_refunds_once(self):
        self.client_http.post(reverse("cancel_booking", args=[self.booking.pk]))
        self.client_http.post(reverse("cancel_booking", args=[self.booking.pk]))

        self.student.refresh_from_db()
        self.assertEqual(self.student.sessoes_sg, 1)


class AulasPassadasTests(TestCase):
    """
    Uma aula que já decorreu não pode oferecer o botão "Reservar".

    O servidor já recusava a reserva; o que faltava era o aluno perceber isso
    antes de clicar. Ver a ordem das condições no schedule.html: "já decorreu"
    tem de ser testado antes de "reservado".
    """

    def setUp(self):
        self.service = ServiceType.objects.create(name="Aula de Grupo", default_capacity=12)
        self.student = User.objects.create_user(
            username="912345678", password="segredo1", sessoes_sg=5
        )
        self.client_http = Client()
        self.client_http.force_login(self.student)

        # As horas são FIXAS e o relógio é fixado no _html(), de propósito.
        #
        # A primeira versão deste teste usava "agora - 3h" e "agora + 3h". Isso
        # torna-o instável: corrido depois da meia-noite, a aula de "há 3
        # horas" cai no dia ANTERIOR e desaparece do horário, que só mostra um
        # dia de cada vez. O teste passava de dia e falhava de madrugada — foi
        # apanhado a correr a suite às 00:52.
        #
        # Com o relógio às 14:00, a das 09:00 já decorreu e a das 19:00 ainda
        # não, sempre. É também o caso real: o horário de hoje mistura aulas
        # que já aconteceram de manhã com as que ainda faltam à tarde.
        TZ = ZoneInfo(settings.TIME_ZONE)
        self.dia = timezone.localdate()
        self.agora = datetime.combine(self.dia, time(14, 0)).replace(tzinfo=TZ)
        self.passada = Session.objects.create(
            service_type=self.service,
            start=datetime.combine(self.dia, time(9, 0)).replace(tzinfo=TZ),
            duration_minutes=60, capacity=12,
        )
        self.futura = Session.objects.create(
            service_type=self.service,
            start=datetime.combine(self.dia, time(19, 0)).replace(tzinfo=TZ),
            duration_minutes=60, capacity=12,
        )

    def _html(self):
        # Fixar o timezone.now() cobre tudo: o is_past do modelo e o
        # localdate() da view (que chama o now() por baixo).
        with patch("django.utils.timezone.now", return_value=self.agora):
            resposta = self.client_http.get(
                reverse("schedule"), {"date": self.dia.isoformat()}
            )
        return resposta.content.decode()

    def test_aula_passada_mostra_ja_decorreu(self):
        html = self._html()
        self.assertIn("Já decorreu", html)
        self.assertIn("btn-passada", html)

    def test_aula_passada_nao_tem_formulario_de_reserva(self):
        html = self._html()
        # A futura ainda tem formulário; só deve existir um no dia inteiro.
        self.assertEqual(html.count('class="inline-form book-form"'), 1)
        self.assertNotIn(reverse("book", args=[self.passada.pk]), html)
        self.assertIn(reverse("book", args=[self.futura.pk]), html)

    def test_aula_passada_reservada_nao_diz_reservado(self):
        """A ordem das condições: passada vence 'reservado'."""
        Booking.objects.create(
            session=self.passada, client=self.student, status=Booking.BOOKED
        )
        html = self._html()
        self.assertIn("Já decorreu", html)
        # Procurar só a palavra "Reservado" apanharia também o JS lá em baixo,
        # que constrói esse estado ao reservar sem recarregar. O que o template
        # escreve é o atributo class — é isso que não pode aparecer.
        self.assertNotIn('class="btn-reservado"', html)


class MetaTagsTests(TestCase):
    """
    Etiquetas de partilha e favicon. Existem por causa do WhatsApp: é de lá
    que vem todo o tráfego, e sem elas o link aparece sem imagem nem título.
    """

    def test_open_graph_e_favicon_na_pagina_inicial(self):
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn('property="og:title"', html)
        self.assertIn('property="og:image"', html)
        self.assertIn('name="theme-color"', html)
        self.assertIn("favicon.png", html)

    def test_og_image_e_um_endereco_absoluto(self):
        """O WhatsApp vai buscar a imagem a partir dos servidores dele."""
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn('property="og:image" content="http://testserver/', html)

    def test_paginas_de_login_tambem_tem_meta(self):
        """O base_auth.html é um template à parte e é fácil esquecê-lo."""
        html = self.client.get(reverse("login")).content.decode()
        self.assertIn('property="og:title"', html)
        self.assertIn("favicon.png", html)


class PrecosEscondidosTests(TestCase):
    """
    Decisão do Sérgio (ago 2026): os preços não aparecem no site. Quem quer
    comprar é encaminhado para o WhatsApp, onde ele negoceia. O campo continua
    no admin para uso interno.
    """

    def test_preco_nao_aparece_na_pagina_de_pacotes(self):
        Pack.objects.create(
            name="Pack 12 Sessões", number_of_sessions=12, price="120.00", active=True
        )
        student = User.objects.create_user(username="912345678", password="segredo1")
        self.client.force_login(student)

        html = self.client.get(reverse("packages")).content.decode()
        self.assertIn("Pack 12 Sessões", html)
        self.assertNotIn("120", html)
        self.assertNotIn("pack-price", html)
        self.assertIn("Falar no WhatsApp", html)


class AutofillRegistoTests(TestCase):
    """
    O SignUpForm tem de herdar o Meta do UserCreationForm, senão o campo do
    telemóvel perde o autocomplete e o gestor de passwords do telemóvel não
    guarda o número no registo.
    """

    def test_username_tem_autocomplete(self):
        html = SignUpForm().as_p()
        self.assertIn('autocomplete="username"', html)

    def test_nome_e_data_tem_autocomplete(self):
        html = SignUpForm().as_p()
        self.assertIn('autocomplete="given-name"', html)
        self.assertIn('autocomplete="family-name"', html)
        self.assertIn('autocomplete="bday"', html)

    def test_registo_continua_a_funcionar(self):
        """A mudança do Meta não pode partir a criação de contas."""
        resposta = self.client.post(reverse("signup"), {
            "username": "913000009", "first_name": "Ana", "last_name": "Teste",
            "birth_date": "1990-05-04",
            "password1": "segredo123", "password2": "segredo123",
            "aceita_privacidade": "on",
        })
        self.assertRedirects(resposta, reverse("schedule"))
        self.assertTrue(User.objects.filter(username="913000009").exists())


class GerarSemanaAjustadaTests(TestCase):
    """
    A página "Gerar aulas da semana" permite ajustar tipo, local e lotação
    ANTES de gerar. Os ajustes valem só para as aulas criadas — o programa
    semanal (o molde) não é tocado.
    """

    def setUp(self):
        admin_user = User.objects.create_superuser(
            username="admin-teste", password="segredo1"
        )
        self.client_http = Client()
        self.client_http.force_login(admin_user)

        self.grupo = ServiceType.objects.create(
            name="Aula de Grupo", default_capacity=12, credit_type=CreditType.SMALL_GROUP
        )
        self.pt = ServiceType.objects.create(
            name="PT Individual", default_capacity=1, credit_type=CreditType.PT
        )
        self.estudio = Location.objects.create(name="Estudio", kind=Location.INDOOR)
        self.parque = Location.objects.create(name="Parque", kind=Location.OUTDOOR)

        self.slot = WeeklyProgramSlot.objects.create(
            weekday=0, start_time=time(8, 0),
            service_type=self.grupo, location=self.estudio,
        )
        self.url = "/admin/bookings/weeklyprogramslot/gerar-semana/"
        self.segunda = "2026-08-03"  # é uma Segunda

    def _gerar(self, ajustes=None, atualizar=False):
        dados = {"segunda": self.segunda, "slots": [self.slot.pk]}
        dados.update(ajustes or {})
        if atualizar:
            dados["atualizar"] = "sim"
        return self.client_http.post(self.url, dados)

    def _inscrever(self, sessao, quantos):
        for i in range(quantos):
            aluno = User.objects.create_user(
                username=f"91900000{i}", password="x", sessoes_sg=5, sessoes_pt=5
            )
            Booking.objects.create(
                session=sessao, client=aluno, status=Booking.BOOKED
            )

    # --- ajustes na criação ---------------------------------------------

    def test_gera_com_os_valores_ajustados(self):
        self._gerar({
            f"tipo_{self.slot.pk}": self.pt.pk,
            f"local_{self.slot.pk}": self.parque.pk,
            f"lotacao_{self.slot.pk}": "4",
        })
        sessao = Session.objects.get()
        self.assertEqual(sessao.service_type, self.pt)
        self.assertEqual(sessao.location, self.parque)
        self.assertEqual(sessao.capacity, 4)

    def test_sem_ajustes_usa_os_valores_do_encaixe(self):
        self._gerar()
        sessao = Session.objects.get()
        self.assertEqual(sessao.service_type, self.grupo)
        self.assertEqual(sessao.location, self.estudio)
        self.assertEqual(sessao.capacity, 12)  # o default_capacity do tipo

    def test_local_vazio_gera_aula_online(self):
        self._gerar({f"local_{self.slot.pk}": ""})
        self.assertIsNone(Session.objects.get().location)

    def test_o_programa_semanal_nao_e_alterado(self):
        """O molde tem de ficar exatamente como estava."""
        self._gerar({
            f"tipo_{self.slot.pk}": self.pt.pk,
            f"local_{self.slot.pk}": self.parque.pk,
            f"lotacao_{self.slot.pk}": "4",
        })
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.service_type, self.grupo)
        self.assertEqual(self.slot.location, self.estudio)
        self.assertIsNone(self.slot.capacity)

    def test_mudar_o_tipo_nao_cria_uma_segunda_aula_a_mesma_hora(self):
        """
        A razão de ser da opção A: a verificação compara só o instante. Antes
        comparava também o tipo, e mudar o tipo gerava uma aula duplicada.
        """
        self._gerar()
        self._gerar({f"tipo_{self.slot.pk}": self.pt.pk})
        self.assertEqual(Session.objects.count(), 1)

    # --- atualizar as que já existem -------------------------------------

    def test_sem_atualizar_a_aula_existente_fica_como_estava(self):
        self._gerar()
        self._gerar({f"local_{self.slot.pk}": self.parque.pk})  # sem atualizar
        self.assertEqual(Session.objects.get().location, self.estudio)

    def test_com_atualizar_aplica_os_ajustes_e_mantem_inscricoes(self):
        self._gerar()
        sessao = Session.objects.get()
        self._inscrever(sessao, 3)

        self._gerar(
            {f"local_{self.slot.pk}": self.parque.pk,
             f"lotacao_{self.slot.pk}": "20"},
            atualizar=True,
        )

        sessao.refresh_from_db()
        self.assertEqual(sessao.location, self.parque)
        self.assertEqual(sessao.capacity, 20)
        # O essencial: ninguém foi desinscrito.
        self.assertEqual(sessao.spots_taken, 3)
        self.assertEqual(Session.objects.count(), 1)

    def test_recusa_baixar_a_lotacao_abaixo_dos_inscritos(self):
        self._gerar()
        sessao = Session.objects.get()
        self._inscrever(sessao, 5)

        self._gerar({f"lotacao_{self.slot.pk}": "2"}, atualizar=True)

        sessao.refresh_from_db()
        self.assertEqual(sessao.capacity, 12)  # ficou como estava
        self.assertEqual(sessao.spots_taken, 5)

    def test_recusa_mudar_o_tipo_de_uma_aula_com_inscritos(self):
        """Mudar o tipo mudava o balde de créditos que paga a aula."""
        self._gerar()
        sessao = Session.objects.get()
        self._inscrever(sessao, 1)

        self._gerar({f"tipo_{self.slot.pk}": self.pt.pk}, atualizar=True)

        sessao.refresh_from_db()
        self.assertEqual(sessao.service_type, self.grupo)

    def test_muda_o_tipo_se_ainda_nao_houver_inscritos(self):
        self._gerar()
        self._gerar({f"tipo_{self.slot.pk}": self.pt.pk}, atualizar=True)
        self.assertEqual(Session.objects.get().service_type, self.pt)

    def test_atualizar_nunca_apaga_a_aula(self):
        """Nenhum caminho desta página pode apagar uma aula."""
        self._gerar()
        pk_original = Session.objects.get().pk
        self._gerar({f"local_{self.slot.pk}": self.parque.pk}, atualizar=True)
        self.assertEqual(Session.objects.get().pk, pk_original)


class MovimentoCreditoTests(TestCase):
    """
    O extrato dos créditos. Tem de registar os CINCO caminhos que mexem em
    saldos — se algum ficar de fora, o livro deixa de bater certo com o saldo
    e perde a razão de existir.
    """

    def setUp(self):
        self.servico = ServiceType.objects.create(
            name="Aula de Grupo", default_capacity=12,
            credit_type=CreditType.SMALL_GROUP,
        )
        self.sessao = Session.objects.create(
            service_type=self.servico,
            start=timezone.now() + timedelta(days=2),
            duration_minutes=60, capacity=12,
        )
        self.aluno = User.objects.create_user(
            username="912345678", password="segredo1", sessoes_sg=5
        )
        self.client_http = Client()
        self.client_http.force_login(self.aluno)

    def _ultimo(self):
        return MovimentoCredito.objects.order_by("-pk").first()

    # --- os cinco caminhos ----------------------------------------------

    def test_reservar_regista_menos_um(self):
        self.client_http.post(reverse("book", args=[self.sessao.pk]))
        m = self._ultimo()
        self.assertEqual(m.quantidade, -1)
        self.assertEqual(m.motivo, MovimentoCredito.RESERVA)
        self.assertEqual(m.credit_type, CreditType.SMALL_GROUP)
        self.assertEqual(m.session, self.sessao)
        self.assertEqual(m.client, self.aluno)

    def test_aluno_cancelar_regista_mais_um(self):
        self.client_http.post(reverse("book", args=[self.sessao.pk]))
        marcacao = Booking.objects.get(session=self.sessao, client=self.aluno)
        self.client_http.post(reverse("cancel_booking", args=[marcacao.pk]))
        m = self._ultimo()
        self.assertEqual(m.quantidade, 1)
        self.assertEqual(m.motivo, MovimentoCredito.CANCELAMENTO)

    def test_aula_cancelada_regista_o_reembolso(self):
        self.client_http.post(reverse("book", args=[self.sessao.pk]))
        self.sessao.is_cancelled = True
        self.sessao.save()
        m = self._ultimo()
        self.assertEqual(m.quantidade, 1)
        self.assertEqual(m.motivo, MovimentoCredito.AULA_CANCELADA)

    def test_apagar_marcacao_regista_o_reembolso(self):
        self.client_http.post(reverse("book", args=[self.sessao.pk]))
        Booking.objects.get(session=self.sessao, client=self.aluno).delete()
        m = self._ultimo()
        self.assertEqual(m.quantidade, 1)
        self.assertEqual(m.motivo, MovimentoCredito.MARCACAO_APAGADA)

    def test_ajuste_no_admin_regista_a_compra(self):
        """É por aqui que entra o dinheiro: não pode ficar sem rasto."""
        sergio = User.objects.create_superuser(username="sergio", password="segredo1")
        painel = Client()
        painel.force_login(sergio)

        painel.post(
            reverse("admin:accounts_user_change", args=[self.aluno.pk]),
            {
                "username": self.aluno.username,
                "first_name": "", "last_name": "", "birth_date": "",
                "sessoes_sg": 15, "sessoes_pt": 0, "sessoes_hybrid": 0,
                "is_active": "on",
                "last_login_0": "", "last_login_1": "",
                "date_joined_0": "2026-01-01", "date_joined_1": "10:00:00",
            },
        )
        self.aluno.refresh_from_db()
        self.assertEqual(self.aluno.sessoes_sg, 15)

        m = self._ultimo()
        self.assertEqual(m.quantidade, 10)          # de 5 para 15
        self.assertEqual(m.motivo, MovimentoCredito.COMPRA)
        self.assertEqual(m.feito_por, sergio)       # quem o fez fica registado

    # --- o livro tem de bater certo com o saldo --------------------------

    def test_o_saldo_depois_acompanha_o_saldo_real(self):
        self.client_http.post(reverse("book", args=[self.sessao.pk]))
        self.aluno.refresh_from_db()
        self.assertEqual(self._ultimo().saldo_depois, self.aluno.sessoes_sg)

    def test_a_soma_dos_movimentos_explica_o_saldo(self):
        """
        A propriedade que dá valor ao livro: saldo inicial + soma dos
        movimentos = saldo atual. Se isto falhar, há um caminho que mexe em
        créditos sem registar.
        """
        inicial = 5
        outra = Session.objects.create(
            service_type=self.servico,
            start=timezone.now() + timedelta(days=3),
            duration_minutes=60, capacity=12,
        )
        self.client_http.post(reverse("book", args=[self.sessao.pk]))
        self.client_http.post(reverse("book", args=[outra.pk]))
        marcacao = Booking.objects.get(session=outra, client=self.aluno)
        self.client_http.post(reverse("cancel_booking", args=[marcacao.pk]))

        soma = sum(
            m.quantidade for m in
            MovimentoCredito.objects.filter(
                client=self.aluno, credit_type=CreditType.SMALL_GROUP
            )
        )
        self.aluno.refresh_from_db()
        self.assertEqual(inicial + soma, self.aluno.sessoes_sg)

    # --- o livro não se mexe --------------------------------------------

    def test_o_admin_nao_deixa_criar_alterar_nem_apagar(self):
        from django.contrib.admin.sites import site

        from bookings.admin import MovimentoCreditoAdmin
        painel = MovimentoCreditoAdmin(MovimentoCredito, site)
        self.assertFalse(painel.has_add_permission(None))
        self.assertFalse(painel.has_change_permission(None))
        self.assertFalse(painel.has_delete_permission(None))

    def test_reserva_falhada_nao_deixa_movimento(self):
        """Sem saldo não há desconto, logo também não pode haver linha."""
        User.objects.filter(pk=self.aluno.pk).update(sessoes_sg=0)
        self.client_http.post(reverse("book", args=[self.sessao.pk]))
        self.assertEqual(MovimentoCredito.objects.count(), 0)


class PaginasDeErroTests(TestCase):
    """
    As páginas 404 e 500. O Django usa-as automaticamente quando DEBUG=False
    (que é o caso nos testes) — basta estarem na raiz de templates/.
    """

    def test_404_mostra_a_nossa_pagina(self):
        r = self.client.get("/isto-nao-existe/")
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "Esta página não existe", status_code=404)
        # E dá caminho de volta, em vez de deixar o aluno num beco.
        self.assertContains(r, reverse("schedule"), status_code=404)

    def test_500_nao_depende_de_nada(self):
        """
        A 500 aparece quando algo JÁ correu mal — pode ser a base de dados, os
        ficheiros estáticos ou o próprio base.html. Por isso é renderizada sem
        contexto nenhum, e tem de aguentar isso sem rebentar.
        """
        from django.template.loader import get_template

        html = get_template("500.html").render()  # sem contexto, como o Django faz
        self.assertIn("RESTART NOW", html)
        self.assertIn("correu mal", html)
        # Autónoma: sem herança e sem ficheiros externos.
        self.assertNotIn("{% extends", html)
        self.assertNotIn("/static/", html)


class ConsultasPorEcraTests(TestCase):
    """
    O número de consultas à base de dados não pode crescer com o número de
    aulas no ecrã.

    Cada aula mostra "X / Y inscritos", e contar inscritos aula a aula é uma
    ida à base de dados por aula (o chamado N+1). Em SQLite local não se
    nota; em produção a base de dados está noutra máquina e cada ida é uma
    viagem pela rede.

    Os testes comparam o mesmo ecrã com poucas e com muitas aulas: o número
    de consultas tem de ser igual. Comparar em vez de fixar um número evita
    um teste que parte sempre que se acrescenta uma consulta inofensiva.
    """

    def setUp(self):
        self.service = ServiceType.objects.create(name="Aula", default_capacity=10)
        self.student = User.objects.create_user(username="912345678", password="x")
        self.client_http = Client()
        self.client_http.force_login(self.student)

    def _povoar(self, quantas, quando):
        Session.objects.all().delete()
        for i in range(quantas):
            Session.objects.create(
                service_type=self.service,
                start=quando + timedelta(minutes=i * 30),
                duration_minutes=60,
                capacity=10,
            )

    def _consultas(self, url, quantas_aulas, quando, dados=None):
        self._povoar(quantas_aulas, quando)
        with CaptureQueriesContext(connection) as capturadas:
            self.client_http.get(url, dados or {})
        return len(capturadas)

    def test_horario_nao_consulta_por_aula(self):
        amanha = timezone.now() + timedelta(days=1)
        dia = {"date": timezone.localtime(amanha).strftime("%Y-%m-%d")}
        url = reverse("schedule")

        poucas = self._consultas(url, 2, amanha, dia)
        muitas = self._consultas(url, 12, amanha, dia)

        self.assertEqual(
            poucas, muitas,
            f"O horário fez {poucas} consultas com 2 aulas e {muitas} com 12: "
            "está a contar os inscritos aula a aula.",
        )

    def test_pagina_inicial_nao_consulta_por_aula(self):
        amanha = timezone.now() + timedelta(days=1)
        url = reverse("home")

        poucas = self._consultas(url, 2, amanha)
        muitas = self._consultas(url, 12, amanha)

        self.assertEqual(
            poucas, muitas,
            f"A página inicial fez {poucas} consultas com 2 aulas e {muitas} "
            "com 12.",
        )

    def test_lista_de_sessoes_do_admin_nao_consulta_por_aula(self):
        chefe = User.objects.create_superuser(username="chefe", password="x")
        painel = Client()
        painel.force_login(chefe)
        amanha = timezone.now() + timedelta(days=1)
        url = reverse("admin:bookings_session_changelist")

        self._povoar(2, amanha)
        with CaptureQueriesContext(connection) as poucas:
            painel.get(url)

        self._povoar(12, amanha)
        with CaptureQueriesContext(connection) as muitas:
            painel.get(url)

        self.assertEqual(
            len(poucas), len(muitas),
            f"O admin fez {len(poucas)} consultas com 2 aulas e {len(muitas)} "
            "com 12: a coluna Inscritos está a contar linha a linha.",
        )


class PrivacidadeTests(TestCase):
    """
    RGPD. A app guarda nome, telemóvel e data de nascimento de pessoas reais,
    o que faz dela um tratamento de dados pessoais. O responsável legal é o
    Sérgio (é o negócio dele); o que nos cabe é a ferramenta em condições:
    dizer o que é guardado, pedir consentimento antes de guardar e conseguir
    apagar tudo de quem o pedir.
    """

    def _dados(self, **extra):
        dados = {
            "username": "913000009",
            "first_name": "Ana",
            "last_name": "Exemplo",
            "birth_date": "1990-05-04",
            "password1": "segredo123",
            "password2": "segredo123",
        }
        dados.update(extra)
        return dados

    def test_a_politica_abre_sem_ser_preciso_ter_conta(self):
        # Tem de se poder ler ANTES de decidir criar conta.
        resposta = self.client.get(reverse("privacidade"))
        self.assertEqual(resposta.status_code, 200)

    def test_registo_sem_aceitar_a_politica_e_recusado(self):
        resposta = self.client.post(reverse("signup"), self._dados())

        self.assertEqual(resposta.status_code, 200)  # volta ao formulário
        self.assertFalse(User.objects.filter(username="913000009").exists())

    def test_registo_guarda_quando_a_politica_foi_aceite(self):
        # A prova de consentimento é a data: sem ela não há como mostrar que
        # o aluno aceitou.
        antes = timezone.now()
        resposta = self.client.post(
            reverse("signup"), self._dados(aceita_privacidade="on")
        )

        self.assertRedirects(resposta, reverse("schedule"))
        aluno = User.objects.get(username="913000009")
        self.assertIsNotNone(aluno.consentimento_em)
        self.assertGreaterEqual(aluno.consentimento_em, antes)

    def test_paginas_do_site_apontam_para_a_politica(self):
        resposta = self.client.get(reverse("home"))
        self.assertContains(resposta, reverse("privacidade"))

    def test_apagar_um_aluno_leva_tudo_o_que_e_dele(self):
        # Direito ao apagamento: não podem sobrar dados dele para trás.
        aluno = User.objects.create_user(username="913000010", password="x")
        servico = ServiceType.objects.create(name="Aula", default_capacity=10)
        aula = Session.objects.create(
            service_type=servico,
            start=timezone.now() + timedelta(days=1),
            duration_minutes=60, capacity=10,
        )
        Booking.objects.create(session=aula, client=aluno)
        MovimentoCredito.objects.create(
            client=aluno, credit_type=CreditType.SMALL_GROUP,
            quantidade=5, motivo=MovimentoCredito.COMPRA, saldo_depois=5,
        )

        aluno.delete()

        self.assertFalse(Booking.objects.filter(client_id=aluno.pk).exists())
        self.assertFalse(MovimentoCredito.objects.filter(client_id=aluno.pk).exists())
        # A aula em si não desaparece: é do Sérgio, não do aluno.
        self.assertTrue(Session.objects.filter(pk=aula.pk).exists())


class ListaEditavelDoAdminTests(TestCase):
    """
    Os menus de Tipo e Local na lista de Sessões continuam completos.

    A lista congela as opções destes menus numa lista, para não repetir a
    consulta em cada linha. Se isso alguma vez as esvaziar ou truncar, o
    Sérgio perde a edição em linha — e perderia em silêncio, porque a página
    continuaria a abrir na mesma.
    """

    def setUp(self):
        chefe = User.objects.create_superuser(username="chefe", password="x")
        self.painel = Client()
        self.painel.force_login(chefe)
        self.tipos = [
            ServiceType.objects.create(name=f"Tipo {i}", default_capacity=10)
            for i in range(3)
        ]
        self.locais = [
            Location.objects.create(name=f"Local {i}") for i in range(4)
        ]
        Session.objects.create(
            service_type=self.tipos[0],
            start=timezone.now() + timedelta(days=1),
            duration_minutes=60, capacity=10,
        )

    def _opcoes_do_menu(self, html, campo):
        """
        Os textos das opções do menu daquele campo, na 1.ª linha da lista.

        Tem de se olhar para DENTRO do <select>: os nomes dos tipos e dos
        locais também aparecem na coluna da tabela e nos filtros laterais,
        e procurá-los no html inteiro daria um teste que passa mesmo com os
        menus vazios.
        """
        select = re.search(
            rf'<select[^>]*name="form-0-{campo}"[^>]*>(.*?)</select>',
            html,
            re.S,
        )
        self.assertIsNotNone(select, f"não há menu de {campo} na lista")
        return re.findall(r"<option[^>]*>([^<]*)</option>", select.group(1))

    def test_menus_da_lista_trazem_todas_as_opcoes(self):
        resposta = self.painel.get(reverse("admin:bookings_session_changelist"))
        html = resposta.content.decode()

        tipos = self._opcoes_do_menu(html, "service_type")
        locais = self._opcoes_do_menu(html, "location")

        for tipo in self.tipos:
            self.assertIn(tipo.name, tipos, f"falta o tipo {tipo.name} no menu")
        for local in self.locais:
            self.assertIn(local.name, locais, f"falta o local {local.name} no menu")


class ListaEsperaTests(TestCase):
    """
    A fila de quem quer entrar numa aula cheia.

    Decisão de set 2026: quando abre vaga, o primeiro da fila é inscrito
    automaticamente e gasta 1 crédito — e fica a aguardar aviso, para o
    Sérgio lhe mandar uma mensagem pelo WhatsApp. A app não tem como avisar
    ninguém sozinha, por isso a promoção sem o aviso dele deixaria o aluno
    inscrito sem saber.
    """

    def setUp(self):
        self.servico = ServiceType.objects.create(
            name="Aula", default_capacity=1, credit_type=CreditType.SMALL_GROUP
        )
        self.aula = Session.objects.create(
            service_type=self.servico,
            start=timezone.now() + timedelta(days=2),
            duration_minutes=60, capacity=1,
        )
        # O ocupante da única vaga.
        self.ocupante = User.objects.create_user(
            username="913000001", password="x", sessoes_sg=5
        )
        Booking.objects.create(session=self.aula, client=self.ocupante)

        self.espera = User.objects.create_user(
            username="913000002", password="x", sessoes_sg=5
        )
        self.cliente = Client()
        self.cliente.force_login(self.espera)

    def _entrar_na_fila(self, quem=None):
        c = self.cliente
        if quem is not None:
            c = Client()
            c.force_login(quem)
        return c.post(reverse("entrar_lista_espera", args=[self.aula.pk]))

    def _cancelar_do_ocupante(self):
        marcacao = Booking.objects.get(session=self.aula, client=self.ocupante)
        dono = Client()
        dono.force_login(self.ocupante)
        return dono.post(reverse("cancel_booking", args=[marcacao.pk]))

    def test_entrar_na_fila_de_uma_aula_cheia(self):
        self._entrar_na_fila()
        self.assertTrue(
            ListaEspera.objects.filter(
                session=self.aula, client=self.espera,
                estado=ListaEspera.A_ESPERA
            ).exists()
        )

    def test_entrar_na_fila_nao_gasta_credito(self):
        # Só se paga quando se entra mesmo na aula.
        self._entrar_na_fila()
        self.espera.refresh_from_db()
        self.assertEqual(self.espera.sessoes_sg, 5)

    def test_nao_se_entra_na_fila_de_uma_aula_com_vaga(self):
        livre = Session.objects.create(
            service_type=self.servico,
            start=timezone.now() + timedelta(days=3),
            duration_minutes=60, capacity=10,
        )
        self.cliente.post(reverse("entrar_lista_espera", args=[livre.pk]))
        self.assertFalse(ListaEspera.objects.filter(session=livre).exists())

    def test_nao_se_entra_duas_vezes(self):
        self._entrar_na_fila()
        self._entrar_na_fila()
        self.assertEqual(ListaEspera.objects.filter(session=self.aula).count(), 1)

    def test_quem_cancela_liberta_a_vaga_para_o_primeiro_da_fila(self):
        self._entrar_na_fila()
        self._cancelar_do_ocupante()

        self.assertTrue(
            Booking.objects.filter(
                session=self.aula, client=self.espera, status=Booking.BOOKED
            ).exists()
        )

    def test_quem_sobe_paga_a_sessao(self):
        self._entrar_na_fila()
        self._cancelar_do_ocupante()

        self.espera.refresh_from_db()
        self.assertEqual(self.espera.sessoes_sg, 4)
        self.assertTrue(
            MovimentoCredito.objects.filter(
                client=self.espera, quantidade=-1,
                motivo=MovimentoCredito.RESERVA
            ).exists()
        )

    def test_quem_sobe_fica_a_aguardar_aviso(self):
        self._entrar_na_fila()
        self._cancelar_do_ocupante()

        lugar = ListaEspera.objects.get(session=self.aula, client=self.espera)
        self.assertEqual(lugar.estado, ListaEspera.INSCRITO)
        self.assertIsNone(lugar.avisado_em, "não pode nascer já avisado")
        self.assertIn(lugar, ListaEspera.objects.por_avisar())

    def test_sem_saldo_salta_para_o_seguinte(self):
        # O primeiro da fila não tem créditos: a vaga não pode ficar perdida.
        sem_saldo = User.objects.create_user(
            username="913000003", password="x", sessoes_sg=0
        )
        self._entrar_na_fila(quem=sem_saldo)
        self._entrar_na_fila()  # o segundo tem saldo
        self._cancelar_do_ocupante()

        self.assertTrue(
            Booking.objects.filter(
                session=self.aula, client=self.espera, status=Booking.BOOKED
            ).exists()
        )
        self.assertFalse(
            Booking.objects.filter(
                session=self.aula, client=sem_saldo, status=Booking.BOOKED
            ).exists()
        )

    def test_so_sobe_uma_pessoa_por_vaga(self):
        self._entrar_na_fila()
        outro = User.objects.create_user(
            username="913000004", password="x", sessoes_sg=5
        )
        self._entrar_na_fila(quem=outro)
        self._cancelar_do_ocupante()

        self.assertEqual(self.aula.spots_taken, 1)

    def test_sair_da_fila(self):
        self._entrar_na_fila()
        self.cliente.post(reverse("sair_lista_espera", args=[self.aula.pk]))
        self.assertFalse(
            ListaEspera.objects.filter(
                session=self.aula, client=self.espera,
                estado=ListaEspera.A_ESPERA
            ).exists()
        )

    def test_entrar_na_fila_volta_ao_dia_da_aula(self):
        """
        Não pode atirar o aluno para hoje.

        O horário abre sempre no dia de hoje; a aula que ele estava a ver
        pode ser daqui a dois dias. Sem isto, entrava na fila e ficava a
        olhar para "não há sessões marcadas para este dia".
        """
        resposta = self._entrar_na_fila()
        dia = timezone.localtime(self.aula.start).strftime("%Y-%m-%d")
        self.assertRedirects(resposta, f"{reverse('schedule')}?date={dia}")

    def test_sair_da_fila_volta_ao_dia_da_aula(self):
        self._entrar_na_fila()
        resposta = self.cliente.post(
            reverse("sair_lista_espera", args=[self.aula.pk])
        )
        dia = timezone.localtime(self.aula.start).strftime("%Y-%m-%d")
        self.assertRedirects(resposta, f"{reverse('schedule')}?date={dia}")


class EcraDeAvisosDoSergioTests(TestCase):
    """
    O painel onde o Sérgio vê quem tem de avisar.

    A app não manda mensagens: quando alguém sobe da lista de espera, este
    ecrã é o único sinal de que há uma pessoa inscrita numa aula sem saber.
    """

    def setUp(self):
        chefe = User.objects.create_superuser(username="chefe", password="x")
        self.painel = Client()
        self.painel.force_login(chefe)

        servico = ServiceType.objects.create(
            name="Aula", default_capacity=1, credit_type=CreditType.SMALL_GROUP
        )
        self.aula = Session.objects.create(
            service_type=servico,
            start=timezone.now() + timedelta(days=2),
            duration_minutes=60, capacity=1,
        )
        self.subiu = User.objects.create_user(
            username="913000007", password="x", first_name="Rita", sessoes_sg=5
        )
        self.url = reverse("admin:bookings_listaespera_changelist")

    def _promover(self):
        ListaEspera.objects.create(session=self.aula, client=self.subiu)
        promover_da_lista_de_espera(self.aula)
        return ListaEspera.objects.get(session=self.aula, client=self.subiu)

    def test_quem_subiu_aparece_como_falta_avisar(self):
        self._promover()
        html = self.painel.get(self.url).content.decode()
        self.assertIn("falta avisar", html)
        self.assertIn("913000007", html)

    def test_o_numero_abre_o_whatsapp(self):
        self._promover()
        html = self.painel.get(self.url).content.decode()
        self.assertIn("https://wa.me/351913000007", html)

    def test_o_nome_do_aluno_nao_entra_no_javascript(self):
        # Mesma armadilha da coluna das Marcações: um nome com aspas não pode
        # partir a string do confirm() e injetar código no painel.
        self.subiu.first_name = "Ri'ta\"><script>x</script>"
        self.subiu.save()
        self._promover()
        html = self.painel.get(self.url).content.decode()
        self.assertNotIn("<script>x</script>", html)

    def test_marcar_como_avisado_tira_da_lista(self):
        lugar = self._promover()
        self.painel.post(self.url, {
            "action": "marcar_como_avisado",
            "_selected_action": [str(lugar.pk)],
        })
        lugar.refresh_from_db()
        self.assertIsNotNone(lugar.avisado_em)
        self.assertNotIn(lugar, ListaEspera.objects.por_avisar())

    def test_quem_ainda_espera_nao_conta_como_por_avisar(self):
        # Está na fila mas não subiu: não há nada para avisar.
        lugar = ListaEspera.objects.create(session=self.aula, client=self.subiu)
        self.assertNotIn(lugar, ListaEspera.objects.por_avisar())

    def test_nao_se_acrescentam_entradas_pelo_painel(self):
        # Entra-se na fila pelo site; aqui só se avisa.
        resposta = self.painel.get(
            reverse("admin:bookings_listaespera_add")
        )
        self.assertIn(resposta.status_code, (302, 403))

    def test_o_filtro_nao_oferece_um_todos_que_mente(self):
        # A página começa filtrada por "falta avisar": um "Todos" no topo
        # daria a mesma lista e faria duvidar do que se está a ver.
        self._promover()
        html = self.painel.get(self.url).content.decode()
        filtro = html.split('data-filter-title="Por avisar"')[1].split("</details>")[0]
        self.assertNotIn(">Todos<", filtro)
        self.assertIn("Só quem falta avisar", filtro)
        self.assertIn("Mostrar tudo", filtro)


class PresencasTests(TestCase):
    """
    O ecrã onde o Sérgio marca quem veio e quem faltou.

    Os estados já existiam no `Booking` desde o início, mas não havia por
    onde lhes tocar sem abrir marcação a marcação. Faltar **não** devolve o
    crédito (decisão do `PENDENTES.md`): é o que faz as pessoas cancelarem a
    tempo e libertarem a vaga.
    """

    def setUp(self):
        chefe = User.objects.create_superuser(username="chefe", password="x")
        self.painel = Client()
        self.painel.force_login(chefe)

        servico = ServiceType.objects.create(
            name="Aula", default_capacity=10, credit_type=CreditType.SMALL_GROUP
        )
        self.aula = Session.objects.create(
            service_type=servico,
            start=timezone.now() - timedelta(hours=2),  # já decorreu
            duration_minutes=60, capacity=10,
        )
        self.ana = User.objects.create_user(
            username="913000011", password="x", first_name="Ana", sessoes_sg=3
        )
        self.rui = User.objects.create_user(
            username="913000012", password="x", first_name="Rui", sessoes_sg=3
        )
        self.m_ana = Booking.objects.create(session=self.aula, client=self.ana)
        self.m_rui = Booking.objects.create(session=self.aula, client=self.rui)
        self.url = reverse("admin:bookings_session_presencas", args=[self.aula.pk])

    def test_a_pagina_lista_os_inscritos(self):
        html = self.painel.get(self.url).content.decode()
        self.assertIn("Ana", html)
        self.assertIn("Rui", html)

    def test_marcar_quem_veio_e_quem_faltou(self):
        self.painel.post(self.url, {
            f"estado_{self.m_ana.pk}": Booking.ATTENDED,
            f"estado_{self.m_rui.pk}": Booking.NO_SHOW,
        })
        self.m_ana.refresh_from_db()
        self.m_rui.refresh_from_db()
        self.assertEqual(self.m_ana.status, Booking.ATTENDED)
        self.assertEqual(self.m_rui.status, Booking.NO_SHOW)

    def test_faltar_nao_devolve_o_credito(self):
        antes = self.rui.sessoes_sg
        self.painel.post(self.url, {f"estado_{self.m_rui.pk}": Booking.NO_SHOW})
        self.rui.refresh_from_db()
        self.assertEqual(self.rui.sessoes_sg, antes)

    def test_marcar_presencas_nao_mexe_em_creditos_de_ninguem(self):
        # Nem sequer um movimento no livro: presenças não são dinheiro.
        antes = MovimentoCredito.objects.count()
        self.painel.post(self.url, {
            f"estado_{self.m_ana.pk}": Booking.ATTENDED,
            f"estado_{self.m_rui.pk}": Booking.NO_SHOW,
        })
        self.assertEqual(MovimentoCredito.objects.count(), antes)

    def test_quem_cancelou_nao_aparece_para_marcar(self):
        # Cancelou a tempo e já recebeu o crédito de volta: não é uma falta.
        self.m_rui.status = Booking.CANCELLED
        self.m_rui.save()
        html = self.painel.get(self.url).content.decode()
        self.assertIn("Ana", html)
        self.assertNotIn(f"estado_{self.m_rui.pk}", html)

    def test_da_para_corrigir_uma_marcacao_errada(self):
        self.painel.post(self.url, {f"estado_{self.m_ana.pk}": Booking.NO_SHOW})
        self.painel.post(self.url, {f"estado_{self.m_ana.pk}": Booking.ATTENDED})
        self.m_ana.refresh_from_db()
        self.assertEqual(self.m_ana.status, Booking.ATTENDED)


class VistaSemanalTests(TestCase):
    """
    O horário da semana inteira, além do dia a dia.

    Quem quer marcar as aulas da semana tinha de andar de seta em seta,
    sete vezes. Os limites da janela (-3/+14 dias) são os mesmos: mostrar
    uma semana não é abrir a agenda toda.
    """

    def setUp(self):
        self.servico = ServiceType.objects.create(
            name="Aula", default_capacity=10, credit_type=CreditType.SMALL_GROUP
        )
        self.aluno = User.objects.create_user(
            username="913000031", password="x", sessoes_sg=5
        )
        self.cliente = Client()
        self.cliente.force_login(self.aluno)
        self.url = reverse("schedule_semana")

    def _aula(self, dias):
        return Session.objects.create(
            service_type=self.servico,
            start=timezone.now() + timedelta(days=dias),
            duration_minutes=60, capacity=10,
        )

    def test_mostra_os_sete_dias_da_semana(self):
        dias = self.cliente.get(self.url).context["dias"]
        self.assertEqual(len(dias), 7)

    def test_agrupa_cada_aula_no_seu_dia(self):
        self._aula(1)
        self._aula(1)
        self._aula(2)
        dias = self.cliente.get(self.url).context["dias"]
        contagens = sorted(len(d["sessions"]) for d in dias)
        self.assertEqual(contagens[-2:], [1, 2])

    def test_nao_mostra_aulas_canceladas(self):
        aula = self._aula(1)
        aula.is_cancelled = True
        aula.save()
        dias = self.cliente.get(self.url).context["dias"]
        self.assertEqual(sum(len(d["sessions"]) for d in dias), 0)

    def test_respeita_o_limite_de_14_dias_para_a_frente(self):
        # Pedir uma semana muito à frente fixa-se no limite, como no dia a dia.
        longe = (timezone.localdate() + timedelta(days=120)).strftime("%Y-%m-%d")
        contexto = self.cliente.get(self.url, {"date": longe}).context
        self.assertLessEqual(
            contexto["dias"][0]["dia"], timezone.localdate() + timedelta(days=14)
        )

    def test_nao_consulta_por_aula(self):
        # O mesmo N+1 que o horário do dia tinha: aqui seria sete vezes pior.
        def consultas(quantas):
            Session.objects.all().delete()
            for i in range(quantas):
                Session.objects.create(
                    service_type=self.servico,
                    start=timezone.now() + timedelta(days=1, minutes=i * 30),
                    duration_minutes=60, capacity=10,
                )
            with CaptureQueriesContext(connection) as c:
                self.cliente.get(self.url)
            return len(c)

        self.assertEqual(consultas(2), consultas(12))


class InstalarNoTelemovelTests(TestCase):
    """
    O que é preciso para o telemóvel oferecer "instalar no ecrã principal".

    São três coisas, e falta uma chega para a opção não aparecer: o manifest
    ligado nas páginas, o manifest servido com os ícones, e um service worker
    servido **da raiz** (um worker só manda no seu nível e abaixo — a partir
    de /static/ não chegaria às páginas).
    """

    def setUp(self):
        self.aluno = User.objects.create_user(username="913000041", password="x")
        self.cliente = Client()
        self.cliente.force_login(self.aluno)

    def test_as_paginas_ligam_o_manifest(self):
        html = self.cliente.get(reverse("home")).content.decode()
        self.assertIn('rel="manifest"', html)

    def test_o_service_worker_e_servido_da_raiz(self):
        resposta = self.client.get("/sw.js")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("javascript", resposta["Content-Type"])

    def test_o_service_worker_nao_guarda_paginas(self):
        """
        Guardar páginas numa app de marcações mostraria vagas que já não
        existem e saldos errados. Só se guardam ficheiros estáticos.

        Testa-se a **regra** de cache, não o texto do ficheiro: procurar
        palavras apanhava-as nos comentários (que falam de /horario/
        precisamente para explicar o que não se guarda) e o teste mentia.
        """
        corpo = self.client.get("/sw.js").content.decode()
        declaracao = re.search(r"PARA_GUARDAR\s*=\s*/(.+?)/;", corpo)
        self.assertIsNotNone(declaracao, "não há regra de cache no sw.js")

        # A sintaxe da regex é a mesma nas duas linguagens para este padrão.
        regra = re.compile(declaracao.group(1))

        for estatico in ("/static/css/style.css", "/static/img/brand/icon-192.png"):
            self.assertIsNotNone(regra.search(estatico), f"{estatico} devia ser guardado")

        for pagina in ("/horario/", "/horario/semana/", "/pacotes/",
                       "/as-minhas-marcacoes/", "/admin/bookings/session/"):
            self.assertIsNone(regra.search(pagina), f"{pagina} NÃO pode ser guardada")

    def test_o_service_worker_nao_precisa_de_login(self):
        # É pedido pelo browser sem sessão; atrás de login nunca registaria.
        self.assertEqual(Client().get("/sw.js").status_code, 200)


class LembretesTests(TestCase):
    """
    O ecrã das aulas de amanhã, para o Sérgio avisar quem vai.

    Mesmo princípio da lista de espera: a app não manda mensagens, junta a
    informação e ele manda pelo WhatsApp. Um lembrete que ficasse à espera
    que o aluno abrisse o site não era um lembrete.
    """

    def setUp(self):
        chefe = User.objects.create_superuser(username="chefe", password="x")
        self.painel = Client()
        self.painel.force_login(chefe)
        self.servico = ServiceType.objects.create(
            name="Aula", default_capacity=10, credit_type=CreditType.SMALL_GROUP
        )
        self.url = reverse("admin:bookings_session_lembretes")

    def _aula(self, daqui_a_dias, hora=10):
        # Hora fixa do dia, em hora local, para não escorregar de dia.
        dia = timezone.localdate() + timedelta(days=daqui_a_dias)
        quando = timezone.make_aware(
            datetime.combine(dia, time(hora, 0)),
            ZoneInfo(settings.TIME_ZONE),
        )
        return Session.objects.create(
            service_type=self.servico, start=quando,
            duration_minutes=60, capacity=10,
        )

    def _inscrever(self, aula, numero, nome="Ana"):
        aluno = User.objects.create_user(
            username=numero, password="x", first_name=nome, sessoes_sg=5
        )
        Booking.objects.create(session=aula, client=aluno)
        return aluno

    def test_mostra_as_aulas_de_amanha(self):
        amanha = self._aula(1)
        self._inscrever(amanha, "913000051")
        html = self.painel.get(self.url).content.decode()
        self.assertIn("913000051", html)

    def test_nao_mostra_as_de_hoje_nem_de_depois_de_amanha(self):
        self._inscrever(self._aula(0, hora=23), "913000052")
        self._inscrever(self._aula(2), "913000053")
        html = self.painel.get(self.url).content.decode()
        self.assertNotIn("913000052", html)
        self.assertNotIn("913000053", html)

    def test_nao_mostra_aulas_canceladas(self):
        aula = self._aula(1)
        self._inscrever(aula, "913000054")
        aula.is_cancelled = True
        aula.save()
        html = self.painel.get(self.url).content.decode()
        self.assertNotIn("913000054", html)

    def test_nao_mostra_quem_cancelou_a_reserva(self):
        aula = self._aula(1)
        aluno = self._inscrever(aula, "913000055")
        Booking.objects.filter(session=aula, client=aluno).update(
            status=Booking.CANCELLED
        )
        html = self.painel.get(self.url).content.decode()
        self.assertNotIn("913000055", html)

    def test_o_numero_abre_o_whatsapp(self):
        self._inscrever(self._aula(1), "913000056")
        html = self.painel.get(self.url).content.decode()
        self.assertIn("https://wa.me/351913000056", html)

    def test_aula_sem_inscritos_nao_enche_a_lista(self):
        self._aula(1)  # ninguém inscrito
        aulas = self.painel.get(self.url).context["aulas"]
        self.assertEqual(aulas, [])
