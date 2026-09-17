import re

from django.contrib.auth.models import AbstractUser
from django.db import models


class CreditType(models.TextChoices):
    """
    As 3 categorias de crédito. Cada aula (via o seu tipo de serviço) aceita
    só o crédito da sua categoria; cada pacote enche só um destes baldes.

    O valor curto ("sg", "pt", "hybrid") é também o sufixo do campo de saldo
    no User — ex.: CreditType.SMALL_GROUP -> User.sessoes_sg. Manter alinhados.
    """

    SMALL_GROUP = "sg", "Small Group"
    PT = "pt", "PT"
    HYBRID = "hybrid", "Hybrid"


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
    # Saldos separados por tipo (ver CreditType). Cada reserva gasta 1 do
    # balde correspondente à aula; cancelar/apagar devolve ao mesmo balde.
    sessoes_sg = models.PositiveIntegerField(
        "Sessões Small Group", default=0,
        help_text="Sessões de Small Group disponíveis.",
    )
    sessoes_pt = models.PositiveIntegerField(
        "Sessões PT", default=0,
        help_text="Sessões de PT (individual) disponíveis.",
    )
    sessoes_hybrid = models.PositiveIntegerField(
        "Sessões Hybrid", default=0,
        help_text="Sessões de Hybrid disponíveis.",
    )
    is_trainer = models.BooleanField(
        "É treinador?",
        default=False,
        help_text="Marca esta opção para quem dá aulas/sessões.",
    )
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    deve_mudar_password = models.BooleanField(
        "Tem de mudar a password?",
        default=False,
        help_text=(
            "Fica marcado quando o treinador gera uma password provisória. "
            "Enquanto estiver marcado, o aluno só consegue abrir a página de "
            "mudar a password — e desmarca-se sozinho quando ele a muda."
        ),
    )
    consentimento_em = models.DateTimeField(
        "Aceitou a política de privacidade em",
        null=True,
        blank=True,
        help_text=(
            "Quando o aluno aceitou a política, no registo. É a prova de "
            "consentimento que o RGPD exige — dizer que ele aceitou não "
            "chega, é preciso poder mostrar quando. Vazio nas contas "
            "criadas no painel (ex.: staff) e nas anteriores a isto existir."
        ),
    )

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

    @property
    def telemovel_whatsapp(self):
        """
        Link para abrir a conversa de WhatsApp com esta pessoa, ou vazio.

        Vazio quando o username não é um telemóvel português — é o caso das
        contas de administração ("admin"), que não devem virar um link que
        abre uma conversa com um número que não existe.
        """
        if not re.fullmatch(r"9\d{8}", self.username or ""):
            return ""
        return f"https://wa.me/351{self.username}"

    @staticmethod
    def campo_saldo(credit_type):
        """Nome do campo de saldo para um tipo de crédito (ex.: 'sessoes_sg')."""
        return f"sessoes_{credit_type}"

    def creditos_de(self, credit_type):
        """Saldo atual de um dado tipo de crédito."""
        return getattr(self, self.campo_saldo(credit_type))

    def saldos_creditos(self):
        """
        Os 3 saldos para mostrar (topo do site). Iterar sobre CreditType faz
        com que um 4º tipo, se algum dia existir, apareça automaticamente
        (bastaria acrescentar o campo correspondente).
        """
        return [
            {"tipo": valor, "label": label, "quantidade": self.creditos_de(valor)}
            for valor, label in CreditType.choices
        ]
