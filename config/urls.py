"""
Mapa de URLs do projeto.
"""
from urllib.parse import quote

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import TemplateView

from accounts.views import ThrottledLoginView, com_travao
from bookings.forms import PhoneLoginForm

# Link de WhatsApp para o aluno pedir ajuda com a password (recuperação = Opção A).
_wa_help = "Olá! Esqueci-me da password da app RESTART NOW. Podes ajudar-me?"
WA_HELP_URL = f"https://wa.me/{settings.SERGIO_WHATSAPP}?text={quote(_wa_help)}"

urlpatterns = [
    # Tem de vir ANTES do admin.site.urls para ganhar o pedido: o login do
    # painel passa a ter o mesmo travão de tentativas do login do site.
    # O reverse de "admin:login" continua a dar este mesmo endereço.
    path("admin/login/", com_travao(admin.site.login)),
    path("admin/", admin.site.urls),
    # Login/logout (por telemóvel). Sem recuperação por email — é via WhatsApp.
    # ThrottledLoginView limita tentativas falhadas (proteção de força bruta).
    path(
        "conta/login/",
        ThrottledLoginView.as_view(
            authentication_form=PhoneLoginForm,
            extra_context={"wa_help_url": WA_HELP_URL},
        ),
        name="login",
    ),
    path("conta/logout/", auth_views.LogoutView.as_view(), name="logout"),
    # O service worker TEM de ser servido da raiz: um worker só manda no seu
    # próprio nível e abaixo, e a partir de /static/ não chegaria às páginas.
    # É por isso que vive em templates/ e não em static/.
    path(
        "sw.js",
        TemplateView.as_view(
            template_name="sw.js", content_type="application/javascript"
        ),
        name="service_worker",
    ),
    # Páginas da aplicação (início, horário, pacotes, marcações):
    path("", include("bookings.urls")),
]

# Em desenvolvimento, deixar o Django servir os ficheiros carregados (media).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Textos do painel de administração
admin.site.site_header = "RESTART NOW"
admin.site.site_title = "RESTART NOW"
admin.site.index_title = "Administração"
