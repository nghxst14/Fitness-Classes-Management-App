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


def _client_ip(request):
    """
    IP real do cliente. Atrás do proxy do Railway, REMOTE_ADDR é o IP do
    proxy (igual para todos) — o IP verdadeiro vem no X-Forwarded-For (o
    primeiro da lista). Em dev não há esse cabeçalho e usa-se REMOTE_ADDR.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "desconhecido")


class ThrottledLoginView(auth_views.LoginView):
    """LoginView do Django com limite de tentativas falhadas."""

    def _chave(self):
        ip = _client_ip(self.request)
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
