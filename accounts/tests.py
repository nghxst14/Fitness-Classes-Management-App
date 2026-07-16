from django.contrib.auth import get_user_model
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
