from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.core.cache import cache
from django.shortcuts import redirect

from bookings.forms import normalizar_telemovel

# Proteção contra força bruta no login: como as passwords são deliberadamente
# simples (mínimo 6 caracteres), sem isto era viável um script testar
# passwords comuns contra um número de telemóvel. Após MAX_TENTATIVAS falhas
# seguidas (mesmo IP + mesmo número), bloqueia durante BLOQUEIO_SEGUNDOS.
MAX_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 15 * 60


class ThrottledLoginView(auth_views.LoginView):
    """LoginView do Django com limite de tentativas falhadas."""

    def _chave(self):
        ip = self.request.META.get("REMOTE_ADDR", "desconhecido")
        numero = normalizar_telemovel(self.request.POST.get("username", ""))
        return f"login-falhas:{ip}:{numero}"

    def post(self, request, *args, **kwargs):
        if cache.get(self._chave(), 0) >= MAX_TENTATIVAS:
            messages.error(
                request,
                "Demasiadas tentativas falhadas. Por segurança, espera "
                "15 minutos antes de tentares outra vez.",
            )
            return redirect("login")
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        chave = self._chave()
        cache.set(chave, cache.get(chave, 0) + 1, BLOQUEIO_SEGUNDOS)
        return super().form_invalid(form)

    def form_valid(self, form):
        # Login com sucesso limpa a contagem (não penaliza um engano antigo).
        cache.delete(self._chave())
        return super().form_valid(form)
