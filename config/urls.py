"""
Mapa de URLs do projeto.

Por agora só temos o painel de administração (/admin/), que é onde o Sérgio
vai gerir horários, marcações, packs e vídeos. As páginas para os alunos
(marcações, biblioteca de vídeos) entram no Bloco 2 e no Bloco 3.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Login, logout e mudança de password (views prontas do Django):
    path("conta/", include("django.contrib.auth.urls")),
    # Biblioteca de vídeos:
    path("", include("library.urls")),
    # As páginas da aplicação (início, marcações, etc.):
    path("", include("bookings.urls")),
]

# Em desenvolvimento, deixar o Django servir os ficheiros carregados (media).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Textos do painel de administração
admin.site.site_header = "Gestão de Treinos"
admin.site.site_title = "Gestão de Treinos"
admin.site.index_title = "Administração"
