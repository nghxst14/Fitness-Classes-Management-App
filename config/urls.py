"""
Mapa de URLs do projeto.
"""
from urllib.parse import quote

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from accounts.views import ThrottledLoginView
from bookings.forms import PhoneLoginForm

# Link de WhatsApp para o aluno pedir ajuda com a password (recuperação = Opção A).
_wa_help = "Olá! Esqueci-me da password da app RESTART NOW. Podes ajudar-me?"
WA_HELP_URL = "https://wa.me/%s?text=%s" % (settings.SERGIO_WHATSAPP, quote(_wa_help))

urlpatterns = [
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
