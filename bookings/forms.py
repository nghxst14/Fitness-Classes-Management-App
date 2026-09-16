import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe

User = get_user_model()


def normalizar_telemovel(valor):
    """
    Limpa o número escrito pelo aluno para uma forma canónica: "912 345 678",
    "912-345-678" e "+351 912345678" ficam todos "912345678".

    Sem isto, o mesmo número escrito de maneiras diferentes criava contas
    duplicadas (a unicidade do username compara a string exata).
    """
    valor = re.sub(r"[\s\-\.\(\)]", "", valor or "")
    # Retira o indicativo de Portugal, se o aluno o escreveu.
    for prefixo in ("+351", "00351"):
        if valor.startswith(prefixo):
            valor = valor[len(prefixo):]
            break
    else:
        if valor.startswith("351") and len(valor) == 12:
            valor = valor[3:]
    return valor


class SignUpForm(UserCreationForm):
    """
    Auto-registo do aluno. O login é pelo número de telemóvel, por isso o
    campo `username` do Django é apresentado como "Telemóvel".
    """

    first_name = forms.CharField(
        label="Nome", max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        label="Apelido", max_length=150, required=False,
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
    )
    birth_date = forms.DateField(
        label="Data de nascimento",
        widget=forms.DateInput(attrs={"type": "date", "autocomplete": "bday"}),
    )
    # O RGPD exige consentimento antes de guardar dados pessoais, e que ele
    # seja um ato deliberado: por isso a caixa nasce vazia e é obrigatória.
    # Pré-marcá-la não valeria como consentimento.
    aceita_privacidade = forms.BooleanField(
        label="Li e aceito a política de privacidade",
        required=True,
        error_messages={
            "required": "Para criares conta tens de aceitar a política de "
                        "privacidade."
        },
    )

    class Meta(UserCreationForm.Meta):
        # Herdar do Meta do UserCreationForm traz o
        # field_classes = {"username": UsernameField}, e com ele o
        # autocomplete="username" e o autocapitalize="none". Sem esta herança
        # o campo era um CharField simples: o gestor de passwords do telemóvel
        # não guardava o número no registo e, no login seguinte, não tinha
        # nada para preencher — o aluno escrevia tudo à mão de cada vez.
        model = User
        fields = ("username", "first_name", "last_name", "birth_date")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Telemóvel"
        self.fields["username"].help_text = "É com este número que vais entrar."
        self.fields["username"].widget.attrs.update(
            {"inputmode": "tel", "placeholder": "9xxxxxxxx"}
        )
        # O rótulo leva o link para a política: pedir que a aceitem sem dar
        # como a ler seria consentimento só no nome. Abre noutro separador
        # para não perder o que já foi escrito no formulário. O reverse() dá
        # um endereço nosso, por isso o mark_safe não introduz risco.
        self.fields["aceita_privacidade"].label = mark_safe(
            f'Li e aceito a <a href="{reverse("privacidade")}" target="_blank" '
            'rel="noopener">política de privacidade</a>'
        )
        # Sem os dois pontos do fim: os outros campos rotulam uma caixa que se
        # preenche ("Nome:"), este é uma frase que se aceita.
        self.fields["aceita_privacidade"].label_suffix = ""

    def clean_username(self):
        """Normaliza e valida o telemóvel (9 dígitos, a começar por 9)."""
        numero = normalizar_telemovel(self.cleaned_data["username"])
        if not re.fullmatch(r"9\d{8}", numero):
            raise forms.ValidationError(
                "Escreve um número de telemóvel português válido "
                "(9 dígitos, a começar por 9)."
            )
        if User.objects.filter(username=numero).exists():
            raise forms.ValidationError(
                "Já existe uma conta com este número. "
                "Se te esqueceste da password, fala com o treinador."
            )
        return numero

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.birth_date = self.cleaned_data["birth_date"]
        # Guarda QUANDO aceitou: é a prova do consentimento.
        user.consentimento_em = timezone.now()
        if commit:
            user.save()
        return user


class PhoneLoginForm(AuthenticationForm):
    """Login por telemóvel (relabela o campo username)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Telemóvel"
        self.fields["username"].widget.attrs.update(
            {"inputmode": "tel", "autofocus": True, "placeholder": "9xxxxxxxx"}
        )

    def clean_username(self):
        """
        Só normaliza (espaços, indicativo) — sem validar o formato, para não
        bloquear contas de staff cujo username não é um número (ex.: "admin").
        """
        return normalizar_telemovel(self.cleaned_data["username"])
