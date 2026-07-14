from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Utilizador da plataforma.

    Estende o utilizador padrão do Django (que já traz username, password,
    email, first_name, last_name) e acrescenta o que nos falta.

    - Alunos: contas normais.
    - Sérgio / staff: têm is_staff=True e acedem ao painel de administração.
    """

    phone = models.CharField(
        "Telemóvel",
        max_length=20,
        blank=True,
        help_text="Opcional. Útil para contacto rápido.",
    )
    is_trainer = models.BooleanField(
        "É treinador?",
        default=False,
        help_text="Marca esta opção para quem dá aulas/sessões.",
    )
    created_at = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Utilizador"
        verbose_name_plural = "Utilizadores"
        ordering = ["first_name", "last_name", "username"]

    def __str__(self):
        # Mostra o nome completo se existir; caso contrário, o username.
        return self.get_full_name() or self.username
