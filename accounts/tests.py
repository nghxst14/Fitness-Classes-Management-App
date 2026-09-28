import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking, MovimentoCredito, ServiceType, Session

from .models import CreditType
from .views import MAX_TENTATIVAS

User = get_user_model()


class LoginThrottleTests(TestCase):
    """Após demasiadas tentativas falhadas, o login fica bloqueado 15 min."""

    def setUp(self):
        cache.clear()  # a contagem vive na cache; começar cada teste limpo
        self.user = User.objects.create_user(
            username="912345678", password="segredo1"
        )
        self.client_http = Client()
        self.url = reverse("login")

    def _tentar(self, password):
        return self.client_http.post(
            self.url, {"username": "912345678", "password": password}
        )

    def test_bloqueia_apos_max_tentativas(self):
        for _ in range(MAX_TENTATIVAS):
            self._tentar("errada")

        # Mesmo com a password CERTA, a 6.ª tentativa é recusada.
        response = self._tentar("segredo1")
        self.assertRedirects(response, self.url)
        self.assertNotIn("_auth_user_id", self.client_http.session)

    def test_login_correto_antes_do_limite_funciona_e_limpa_contagem(self):
        for _ in range(MAX_TENTATIVAS - 1):
            self._tentar("errada")

        response = self._tentar("segredo1")
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client_http.session)

    def test_numero_com_espacos_conta_para_o_mesmo_bloqueio(self):
        # Escrever o número com espaços não deve contornar o limite.
        for _ in range(MAX_TENTATIVAS):
            self.client_http.post(
                self.url, {"username": "912 345 678", "password": "errada"}
            )
        response = self._tentar("segredo1")
        self.assertRedirects(response, self.url)


class AdminLoginThrottleTests(TestCase):
    """
    O /admin/login/ tem de ter o mesmo travão que o login do site.

    Vai haver mais do que um administrador (manutenção + o Sérgio, e no
    futuro outros), e a password do Sérgio será de decorar. Sem travão,
    a porta do painel aceita tentativas a toda a velocidade.
    """

    def setUp(self):
        cache.clear()
        User.objects.create_superuser(username="sergio", password="segredo1")
        self.client_http = Client()
        self.url = "/admin/login/"

    def _tentar(self, password, username="sergio"):
        return self.client_http.post(
            self.url, {"username": username, "password": password}
        )

    def test_bloqueia_apos_max_tentativas(self):
        for _ in range(MAX_TENTATIVAS):
            self._tentar("errada")

        # Mesmo com a password CERTA, a tentativa seguinte tem de ser recusada.
        self._tentar("segredo1")
        self.assertNotIn("_auth_user_id", self.client_http.session)

    def test_login_correto_antes_do_limite_funciona(self):
        for _ in range(MAX_TENTATIVAS - 1):
            self._tentar("errada")

        self._tentar("segredo1")
        self.assertIn("_auth_user_id", self.client_http.session)

    def test_tentativas_somam_entre_o_site_e_o_admin(self):
        # Alternar entre as duas portas não pode dar o dobro das tentativas.
        for _ in range(MAX_TENTATIVAS):
            self.client_http.post(
                reverse("login"), {"username": "sergio", "password": "errada"}
            )

        self._tentar("segredo1")
        self.assertNotIn("_auth_user_id", self.client_http.session)


class CacheDoTravaoTests(TestCase):
    """
    A contagem de tentativas tem de viver fora da memória do processo.

    Com a cache de memória local, cada worker do gunicorn conta as suas
    tentativas (cinco workers = cinco vezes mais tentativas antes de
    bloquear) e um redeploy limpa tudo. O travão parecia existir e na
    prática quase não travava.
    """

    def test_a_cache_nao_e_a_memoria_do_processo(self):
        backend = settings.CACHES["default"]["BACKEND"]
        self.assertNotIn(
            "locmem", backend,
            "a cache do travão voltou a ser a de memória do processo: não é "
            "partilhada entre workers nem sobrevive a um deploy",
        )

    def test_a_cache_guarda_e_devolve(self):
        cache.set("prova-travao", 3, 60)
        self.assertEqual(cache.get("prova-travao"), 3)


class PermissoesDoSergioTests(TestCase):
    """
    O Sérgio gere o dia-a-dia mas não mexe em contas de administração.

    Decisão de set 2026: vai haver mais do que um admin. O Sérgio precisa de
    dar créditos, cancelar aulas e gerir alunos, mas criar ou apagar
    administradores fica só com o André — é o engano que não tem volta.
    """

    def setUp(self):
        self.sergio = User.objects.create_user(
            username="913111111", password="x", is_staff=True
        )
        # O Sérgio é staff com as permissões todas de utilizadores, menos o
        # poder sobre contas de administração (que é o que estamos a testar).
        permissoes = Permission.objects.filter(
            content_type__app_label="accounts", content_type__model="user"
        )
        self.sergio.user_permissions.set(permissoes)
        self.andre = User.objects.create_superuser(username="andre", password="x")
        self.aluno = User.objects.create_user(username="913222222", password="x")

        self.painel = Client()
        self.painel.force_login(self.sergio)

    def test_sergio_pode_editar_um_aluno(self):
        url = reverse("admin:accounts_user_change", args=[self.aluno.pk])
        self.assertEqual(self.painel.get(url).status_code, 200)

    def test_sergio_nao_pode_abrir_a_ficha_de_um_admin(self):
        url = reverse("admin:accounts_user_change", args=[self.andre.pk])
        resposta = self.painel.get(url)
        self.assertIn(resposta.status_code, (302, 403))

    def test_sergio_nao_pode_apagar_um_admin(self):
        url = reverse("admin:accounts_user_delete", args=[self.andre.pk])
        resposta = self.painel.post(url, {"post": "yes"})
        self.assertIn(resposta.status_code, (302, 403))
        self.assertTrue(User.objects.filter(pk=self.andre.pk).exists())

    def test_sergio_nao_pode_promover_um_aluno_a_admin(self):
        # O caminho indireto: dar is_staff a alguém seria criar um admin.
        url = reverse("admin:accounts_user_change", args=[self.aluno.pk])
        html = self.painel.get(url).content.decode()
        self.assertNotIn('name="is_superuser"', html)
        self.assertNotIn('name="is_staff"', html)

    def test_o_andre_continua_a_poder_tudo(self):
        painel_andre = Client()
        painel_andre.force_login(self.andre)
        url = reverse("admin:accounts_user_change", args=[self.andre.pk])
        self.assertEqual(painel_andre.get(url).status_code, 200)


class HistoricoDoAlunoTests(TestCase):
    """
    A página que responde a "porque é que eu tenho 5 créditos?".

    O livro de movimentos já guardava a resposta desde set 2026, mas estava
    espalhado por uma lista geral de todos os alunos. Aqui junta-se o que é
    de uma pessoa: os saldos, o extrato e as aulas a que foi.
    """

    def setUp(self):
        chefe = User.objects.create_superuser(username="chefe", password="x")
        self.painel = Client()
        self.painel.force_login(chefe)

        self.aluna = User.objects.create_user(
            username="913000021", password="x", first_name="Ana", sessoes_sg=4
        )
        servico = ServiceType.objects.create(
            name="Aula", default_capacity=10, credit_type=CreditType.SMALL_GROUP
        )
        self.aula = Session.objects.create(
            service_type=servico,
            start=timezone.now() - timedelta(days=1),
            duration_minutes=60, capacity=10,
        )
        Booking.objects.create(
            session=self.aula, client=self.aluna, status=Booking.ATTENDED
        )
        MovimentoCredito.objects.create(
            client=self.aluna, credit_type=CreditType.SMALL_GROUP,
            quantidade=5, motivo=MovimentoCredito.COMPRA, saldo_depois=5,
        )
        MovimentoCredito.objects.create(
            client=self.aluna, credit_type=CreditType.SMALL_GROUP,
            quantidade=-1, motivo=MovimentoCredito.RESERVA,
            saldo_depois=4, session=self.aula,
        )
        self.url = reverse("admin:accounts_user_historico", args=[self.aluna.pk])

    def test_mostra_o_extrato_de_creditos(self):
        html = self.painel.get(self.url).content.decode()
        self.assertIn("Créditos adicionados", html)
        self.assertIn("Reserva de aula", html)

    def test_mostra_as_aulas_do_aluno(self):
        html = self.painel.get(self.url).content.decode()
        self.assertIn("Compareceu", html)

    def test_mostra_os_saldos_atuais(self):
        html = self.painel.get(self.url).content.decode()
        self.assertIn("Small Group", html)

    def test_so_mostra_o_que_e_deste_aluno(self):
        # Verifica-se o que foi para o template, não o HTML: procurar um
        # número solto na página inteira dá falsos positivos (aparece em
        # cores, tokens e caminhos) e o teste passaria a mentir.
        outro = User.objects.create_user(username="913000022", password="x")
        MovimentoCredito.objects.create(
            client=outro, credit_type=CreditType.PT,
            quantidade=99, motivo=MovimentoCredito.COMPRA, saldo_depois=99,
        )
        Booking.objects.create(session=self.aula, client=outro)

        resposta = self.painel.get(self.url)

        self.assertEqual(
            {m.client_id for m in resposta.context["movimentos"]},
            {self.aluna.pk},
        )
        self.assertEqual(
            {m.client_id for m in resposta.context["marcacoes"]},
            {self.aluna.pk},
        )

    def test_o_sergio_nao_ve_o_historico_de_um_admin(self):
        # Mesma regra das fichas: contas de administração são fora do alcance.
        sergio = User.objects.create_user(
            username="913111222", password="x", is_staff=True
        )
        sergio.user_permissions.set(
            Permission.objects.filter(content_type__app_label="accounts")
        )
        painel_sergio = Client()
        painel_sergio.force_login(sergio)
        andre = User.objects.create_superuser(username="andre2", password="x")

        resposta = painel_sergio.get(
            reverse("admin:accounts_user_historico", args=[andre.pk])
        )
        self.assertIn(resposta.status_code, (302, 403))


class WhatsAppNaFichaTests(TestCase):
    """
    Abrir a conversa com o aluno a partir da ficha dele.

    O Sérgio abre a ficha para dar créditos e a seguir quer dizer-lhe que já
    os tem. Sem isto, tinha de copiar o número e procurá-lo no telemóvel.
    O padrão já existia nas Marcações e na Lista de espera; faltava aqui.
    """

    def setUp(self):
        self.chefe = User.objects.create_superuser(username="chefe", password="x")
        self.painel = Client()
        self.painel.force_login(self.chefe)
        self.aluno = User.objects.create_user(
            username="913500500", password="x",
            first_name="Joana", last_name="Silva",
        )

    def _ficha(self, utilizador):
        return self.painel.get(
            reverse("admin:accounts_user_change", args=[utilizador.pk])
        ).content.decode()

    def test_a_ficha_do_aluno_tem_link_de_whatsapp(self):
        self.assertIn("https://wa.me/351913500500", self._ficha(self.aluno))

    def test_a_lista_tem_link_de_whatsapp(self):
        # É na lista que ele dá os créditos; avisar dali poupa abrir a ficha.
        html = self.painel.get(reverse("admin:accounts_user_changelist")).content.decode()
        self.assertIn("https://wa.me/351913500500", html)

    def test_conta_sem_numero_nao_tem_link(self):
        # O "chefe" não é um telemóvel: não há conversa para abrir.
        html = self._ficha(self.chefe)
        self.assertNotIn("wa.me/351chefe", html)
        self.assertNotIn(">https://wa.me/", html)

    def test_o_nome_do_aluno_nao_entra_no_javascript(self):
        # A mesma armadilha da coluna das Marcações: um nome com aspas não
        # pode partir a string do confirm e injetar código no painel.
        self.aluno.first_name = 'Jo"><script>x</script>'
        self.aluno.save()
        self.assertNotIn("<script>x</script>", self._ficha(self.aluno))

    def test_a_coluna_do_whatsapp_e_um_icone_e_nao_texto(self):
        """
        O "conversar" gastava largura numa tabela que já tem dez colunas.

        Um ícone diz a mesma coisa em muito menos espaço — e nesta tabela o
        número já está na coluna ao lado, por isso o texto não acrescentava
        nada.
        """
        lista = self.painel.get(
            reverse("admin:accounts_user_changelist")
        ).content.decode()
        linha = [
            b for b in lista.split("<tr")
            if "913500500" in b and "field-whatsapp" in b
        ][0]
        coluna = linha.split('class="field-whatsapp">')[1].split("</td>")[0]

        self.assertNotIn("conversar", coluna)
        self.assertIn("whatsapp.svg", coluna)
        # Continua a levar ao mesmo sítio.
        self.assertIn("https://wa.me/351913500500", coluna)

    def test_o_icone_diz_o_que_e_a_quem_nao_o_ve(self):
        # Um ícone sem texto alternativo é invisível para um leitor de ecrã.
        lista = self.painel.get(
            reverse("admin:accounts_user_changelist")
        ).content.decode()
        linha = [
            b for b in lista.split("<tr")
            if "913500500" in b and "field-whatsapp" in b
        ][0]
        coluna = linha.split('class="field-whatsapp">')[1].split("</td>")[0]
        self.assertIn("alt=", coluna)

    def test_a_coluna_nao_tem_texto_nenhum(self):
        """
        Nos Utilizadores o nome de conta É o telemóvel.

        Repeti-lo na coluna do lado não acrescentava nada, e a palavra
        "conversar" que lá esteve gastava largura para dizer o que o símbolo
        diz de relance. A coluna passou a ser só o ícone. (Nas Marcações e
        na Lista de espera continua a mostrar o número: lá a coluna do lado
        tem o nome, não o número.)
        """
        lista = self.painel.get(
            reverse("admin:accounts_user_changelist")
        ).content.decode()
        # A linha da Joana, e não a primeira da tabela: a lista vem ordenada
        # por nome e o superuser de teste aparece antes dela.
        linha = [
            bloco for bloco in lista.split("<tr")
            if "913500500" in bloco and "field-whatsapp" in bloco
        ][0]
        coluna = linha.split('class="field-whatsapp">')[1].split("</td>")[0]
        # O que se VÊ, não o html: o número tem de estar no href (é o link),
        # o que não pode é aparecer escrito outra vez ao lado do que já está
        # na coluna Utilizador.
        visivel = re.sub(r"<[^>]+>", "", coluna).strip()
        self.assertEqual(visivel, "", f"a coluna devia ser só o ícone: {visivel!r}")

    def test_a_ficha_diz_o_que_o_link_faz(self):
        ficha = self._ficha(self.aluno)
        campo = ficha.split("field-whatsapp_na_ficha")[1].split("</div>")[0]
        self.assertIn("Abrir conversa", campo)


class PasswordProvisoriaTests(TestCase):
    """
    O Sérgio gera uma password provisória; o aluno é obrigado a trocá-la.

    Substitui o formulário do Django, onde ele teria de **inventar** uma
    password e ditá-la. Assim é um clique, sai aleatória (ninguém põe
    "12345" a toda a gente) e ele nunca fica a saber a password definitiva
    de ninguém — só a provisória, que morre no primeiro uso.
    """

    def setUp(self):
        self.chefe = User.objects.create_superuser(username="chefe", password="x")
        self.painel = Client()
        self.painel.force_login(self.chefe)
        self.aluno = User.objects.create_user(
            username="913500500", password="antiga123",
            first_name="Joana", last_name="Silva",
        )
        self.url = reverse("admin:accounts_user_password_provisoria",
                           args=[self.aluno.pk])

    def _ficha(self):
        return self.painel.get(
            reverse("admin:accounts_user_change", args=[self.aluno.pk])
        ).content.decode()

    def test_o_formulario_nao_fica_dentro_do_formulario_da_ficha(self):
        """
        Um <form> dentro de outro é descartado pelo browser, sem erro nenhum.

        O botão vive na secção da password, que o admin desenha DENTRO do
        formulário principal — por isso o formulário que ele submete tem de
        estar fora, no fim da página, e ligado por `form="..."`. Se alguém o
        mudar para junto do botão, o botão continua a aparecer e deixa de
        fazer nada. Já aconteceu uma vez.
        """
        html = self._ficha()
        self.assertIn('id="gerar-password-provisoria"', html)
        self.assertIn('form="gerar-password-provisoria"', html)

        entre = html[
            html.index('id="user_form"') : html.index('id="gerar-password-provisoria"')
        ]
        self.assertIn(
            "</form>", entre,
            "o formulário da password abre antes de o da ficha fechar: está "
            "aninhado e o browser vai descartá-lo",
        )

    def test_a_ficha_nao_mostra_o_mecanismo_do_django(self):
        """
        O campo de password do Django não serve a quem vai usar isto.

        Mostrava o algoritmo, as iterações, o salt e o hash — lixo técnico
        que não diz nada ao Sérgio — e um "Reset password" em inglês que
        levava a um formulário onde ele teria de INVENTAR a password. Dois
        caminhos para a mesma coisa, e o do Django é o pior dos dois.
        """
        html = self._ficha()
        self.assertNotIn("pbkdf2", html)
        self.assertNotIn("Reset password", html)
        self.assertNotIn("Raw passwords are not stored", html)

    def test_o_botao_esta_na_seccao_da_password(self):
        # E não no topo da página: pertence ao pé do que diz respeito.
        html = self._ficha()
        self.assertIn("Gerar password provisória", html)
        posicao_seccao = html.index("field-acao_password")
        posicao_topo = html.index('class="object-tools"')
        self.assertGreater(
            posicao_seccao, posicao_topo,
            "o botão continua na barra do topo em vez da secção da password",
        )

    def test_gerar_muda_a_password(self):
        self.painel.post(self.url)
        self.aluno.refresh_from_db()
        self.assertFalse(self.aluno.check_password("antiga123"))

    def test_gerar_marca_que_tem_de_mudar(self):
        self.painel.post(self.url)
        self.aluno.refresh_from_db()
        self.assertTrue(self.aluno.deve_mudar_password)

    def test_a_password_e_mostrada_ao_sergio(self):
        # Ele tem de a poder ler para a mandar; é a única vez que aparece.
        resposta = self.painel.post(self.url, follow=True)
        avisos = " ".join(str(m) for m in resposta.context["messages"])
        self.assertRegex(avisos, r"[a-z0-9]{6,}")

    def test_so_por_post(self):
        # Um GET não pode mudar a password de ninguém (nem um link visitado
        # por engano, nem um prefetch do browser).
        self.painel.get(self.url)
        self.aluno.refresh_from_db()
        self.assertTrue(self.aluno.check_password("antiga123"))

    def test_nao_se_gera_para_uma_conta_de_admin(self):
        # O Sérgio não reinicia a password do André.
        sergio = User.objects.create_user(
            username="913111111", password="x", is_staff=True
        )
        permissoes = Permission.objects.filter(
            content_type__app_label="accounts", content_type__model="user"
        )
        sergio.user_permissions.set(permissoes)
        painel_sergio = Client()
        painel_sergio.force_login(sergio)

        resposta = painel_sergio.post(
            reverse("admin:accounts_user_password_provisoria",
                    args=[self.chefe.pk])
        )
        self.assertIn(resposta.status_code, (302, 403))
        self.chefe.refresh_from_db()
        self.assertTrue(self.chefe.check_password("x"))


class MudarPasswordTests(TestCase):
    """O aluno muda a sua password, e é obrigado a fazê-lo se veio de uma provisória."""

    def setUp(self):
        self.aluno = User.objects.create_user(
            username="913500500", password="provisoria1", sessoes_sg=3
        )
        self.cliente = Client()
        self.cliente.force_login(self.aluno)
        self.url = reverse("mudar_password")

    def _mudar(self, atual="provisoria1", nova="minhanova1"):
        return self.cliente.post(self.url, {
            "old_password": atual, "new_password1": nova, "new_password2": nova,
        })

    def test_o_aluno_pode_mudar_a_sua_password(self):
        self._mudar()
        self.aluno.refresh_from_db()
        self.assertTrue(self.aluno.check_password("minhanova1"))

    def test_mudar_limpa_a_obrigacao(self):
        self.aluno.deve_mudar_password = True
        self.aluno.save()
        self._mudar()
        self.aluno.refresh_from_db()
        self.assertFalse(self.aluno.deve_mudar_password)

    def test_quem_tem_de_mudar_e_levado_para_la(self):
        self.aluno.deve_mudar_password = True
        self.aluno.save()
        resposta = self.cliente.get(reverse("schedule"))
        self.assertRedirects(resposta, self.url)

    def test_quem_tem_de_mudar_ainda_consegue_sair(self):
        # Ficar preso sem poder sair seria pior do que o problema.
        self.aluno.deve_mudar_password = True
        self.aluno.save()
        resposta = self.cliente.post(reverse("logout"))
        self.assertNotEqual(resposta.status_code, 500)

    def test_depois_de_mudar_navega_normalmente(self):
        self.aluno.deve_mudar_password = True
        self.aluno.save()
        self._mudar()
        self.assertEqual(self.cliente.get(reverse("schedule")).status_code, 200)

    def test_quem_nao_tem_de_mudar_nao_e_incomodado(self):
        self.assertEqual(self.cliente.get(reverse("schedule")).status_code, 200)
