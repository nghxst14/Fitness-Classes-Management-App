from functools import wraps

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.core.cache import cache
from django.shortcuts import redirect
from django.urls import reverse_lazy

from bookings.forms import normalizar_telemovel

# Proteção contra força bruta no login: como as passwords são deliberadamente
# simples (mínimo 6 caracteres), sem isto era viável um script testar
# passwords comuns contra um número de telemóvel. Após MAX_TENTATIVAS falhas
# seguidas (mesmo IP + mesmo número), bloqueia durante BLOQUEIO_SEGUNDOS.
MAX_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 15 * 60

MENSAGEM_BLOQUEIO = (
    "Demasiadas tentativas falhadas. Por segurança, espera "
    "15 minutos antes de tentares outra vez."
)


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


def _chave_falhas(request, username):
    """
    Chave da contagem: uma por (IP + conta tentada).

    O nome passa pela normalização dos telemóveis para que "912 345 678" e
    "912345678" contem para o mesmo bloqueio. Num nome de staff ("sergio")
    a normalização não tem nada para limpar e devolve-o tal como está.
    """
    ip = _client_ip(request)
    conta = normalizar_telemovel(username or "")
    return f"login-falhas:{ip}:{conta}"


def _bloqueado(chave):
    return cache.get(chave, 0) >= MAX_TENTATIVAS


def _registar_falha(chave):
    cache.set(chave, cache.get(chave, 0) + 1, BLOQUEIO_SEGUNDOS)


class ThrottledLoginView(auth_views.LoginView):
    """LoginView do Django com limite de tentativas falhadas."""

    def _chave(self):
        return _chave_falhas(self.request, self.request.POST.get("username", ""))

    def post(self, request, *args, **kwargs):
        if _bloqueado(self._chave()):
            messages.error(request, MENSAGEM_BLOQUEIO)
            return redirect("login")
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        _registar_falha(self._chave())
        return super().form_invalid(form)

    def form_valid(self, form):
        # Login com sucesso limpa a contagem (não penaliza um engano antigo).
        cache.delete(self._chave())
        return super().form_valid(form)


def com_travao(view_de_login):
    """
    Põe o mesmo travão de tentativas à volta de uma view de login.

    Existe para o login do painel (`/admin/login/`), que o Django traz sem
    limite nenhum — e que passa a ser a porta de mais do que uma conta de
    administrador. Em vez de reescrever a página do admin, que tem template
    e contexto próprios, deixa-se a view dele fazer o trabalho e conta-se as
    falhas à volta: ela redireciona (302) quando entra e volta a desenhar o
    formulário (200) quando a password falha.

    A contagem usa a **mesma** chave do login do site, de propósito: as duas
    portas dão à mesma conta, e alternar entre elas não pode render o dobro
    das tentativas.
    """

    @wraps(view_de_login)
    def wrapper(request, *args, **kwargs):
        chave = _chave_falhas(request, request.POST.get("username", ""))

        if request.method == "POST" and _bloqueado(chave):
            messages.error(request, MENSAGEM_BLOQUEIO)
            # Redirecionar descarta o POST; o GET que se segue volta a
            # mostrar a página de login, já com a mensagem.
            return redirect(request.get_full_path())

        resposta = view_de_login(request, *args, **kwargs)

        if request.method == "POST":
            if resposta.status_code == 200:
                _registar_falha(chave)
            else:
                cache.delete(chave)
        return resposta

    return wrapper


class MudarPasswordView(auth_views.PasswordChangeView):
    """
    O aluno escolhe uma password nova.

    Pede a atual, como o Django faz por omissão. Quem vem de uma provisória
    tem-na à mão (acabou de entrar com ela), e para quem está só a trocar a
    sua é a proteção contra alguém que lhe apanhe o telemóvel desbloqueado.

    Ao gravar, limpa o `deve_mudar_password`: é o que solta o aluno do
    middleware que o trazia sempre para esta página.
    """

    template_name = "registration/mudar_password.html"
    success_url = reverse_lazy("schedule")

    def form_valid(self, form):
        resposta = super().form_valid(form)
        if self.request.user.deve_mudar_password:
            self.request.user.deve_mudar_password = False
            self.request.user.save(update_fields=["deve_mudar_password"])
        messages.success(self.request, "Password alterada. Já está a valer.")
        return resposta
