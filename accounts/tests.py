from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

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
