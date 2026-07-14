from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Video


@login_required
def video_list(request):
    """
    Lista os vídeos publicados, prontos a agrupar por categoria no template.
    Acesso: qualquer utilizador com sessão iniciada.
    """
    videos = (
        Video.objects.filter(published=True)
        .select_related("category")
        .order_by("category__order", "category__name", "order", "-created_at")
    )
    return render(request, "library/video_list.html", {"videos": videos})


@login_required
def video_detail(request, pk):
    """Mostra um vídeo com o leitor incorporado."""
    video = get_object_or_404(Video, pk=pk, published=True)
    return render(request, "library/video_detail.html", {"video": video})
