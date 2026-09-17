"""Obriga quem tem password provisória a escolher outra antes de continuar."""
from django.shortcuts import redirect
from django.urls import reverse


class ForcarMudancaDePassword:
    """
    Quem entrou com uma password provisória só vai a um sítio: mudá-la.

    Sem isto, a provisória — que passou por uma conversa de WhatsApp e que o
    treinador conhece — ficava a valer indefinidamente para quem não se
    lembrasse de a trocar. Que é toda a gente.

    Ficam de fora as páginas de que ele precisa para sair desse estado (a
    própria mudança, o logout) e a política de privacidade, que tem de estar
    sempre acessível. O painel também fica de fora: quem é staff não passa
    por aqui, e prendê-lo dentro do site impedia-o de resolver o problema.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        utilizador = getattr(request, "user", None)
        if (
            utilizador is not None
            and utilizador.is_authenticated
            and getattr(utilizador, "deve_mudar_password", False)
            and not utilizador.is_staff
            and not self._pode_passar(request)
        ):
            return redirect("mudar_password")
        return self.get_response(request)

    @staticmethod
    def _pode_passar(request):
        livres = {
            reverse("mudar_password"),
            reverse("logout"),
            reverse("login"),
            reverse("privacidade"),
        }
        return request.path in livres or request.path.startswith(
            ("/admin/", "/static/", "/media/")
        )
