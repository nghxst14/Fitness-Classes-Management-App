from django.db import models


class VideoCategory(models.Model):
    """Categoria/secção para organizar os vídeos (ex.: 'Mobilidade', 'Core')."""

    name = models.CharField("Nome", max_length=100)
    order = models.PositiveIntegerField("Ordem", default=0)

    class Meta:
        verbose_name = "Categoria de vídeo"
        verbose_name_plural = "Categorias de vídeo"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Video(models.Model):
    """
    Um vídeo de treino.

    Não guardamos o ficheiro de vídeo — ele vive no YouTube ou no Vimeo.
    Guardamos só o identificador para o mostrarmos incorporado ('embed').

    Como encontrar o ID:
    - YouTube: no link https://www.youtube.com/watch?v=ABC123  → ID = ABC123
    - Vimeo:   no link https://vimeo.com/123456789            → ID = 123456789
    """

    YOUTUBE = "youtube"
    VIMEO = "vimeo"
    PROVIDER_CHOICES = [(YOUTUBE, "YouTube"), (VIMEO, "Vimeo")]

    title = models.CharField("Título", max_length=150)
    description = models.TextField("Descrição", blank=True)
    category = models.ForeignKey(
        VideoCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="videos",
        verbose_name="Categoria",
    )
    provider = models.CharField(
        "Plataforma", max_length=10, choices=PROVIDER_CHOICES, default=YOUTUBE
    )
    video_id = models.CharField(
        "ID do vídeo",
        max_length=100,
        help_text="Só o identificador, não o link inteiro (ver ajuda nos exemplos).",
    )
    members_only = models.BooleanField(
        "Só para alunos com sessão iniciada",
        default=True,
        help_text="Se ativo, só utilizadores com conta iniciada podem ver.",
    )
    published = models.BooleanField("Publicado", default=True)
    order = models.PositiveIntegerField("Ordem", default=0)
    created_at = models.DateTimeField("Adicionado em", auto_now_add=True)

    class Meta:
        verbose_name = "Vídeo"
        verbose_name_plural = "Vídeos"
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def embed_url(self):
        """URL para incorporar o vídeo numa página (iframe)."""
        if self.provider == self.YOUTUBE:
            return f"https://www.youtube.com/embed/{self.video_id}"
        if self.provider == self.VIMEO:
            return f"https://player.vimeo.com/video/{self.video_id}"
        return ""
