from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Utilizador da plataforma.

    O login é feito pelo **número de telemóvel**: guardamos o número no campo
    `username` do Django (que é o identificador de início de sessão). Assim
    aproveitamos toda a autenticação pronta do Django sem complicações.

    - Alunos: contas normais, com saldo de créditos.
    - Sérgio / staff: têm is_staff=True e acedem ao painel de administração.
    """

    birth_date = models.DateField(
        "Data de nascimento",
        null=True,
        blank=True,
        help_text="Usada para o Sérgio ser avisado dos aniversários.",
    )
    credits = models.PositiveIntegerField(
        "Créditos (sessões)",
        default=0,
        help_text="Sessões disponíveis. Cada reserva gasta 1 crédito.",
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
        return self.get_full_name() or self.username

    @property
    def phone(self):
        """O telemóvel é o próprio username (identificador de login)."""
        return self.username
