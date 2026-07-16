import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

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

    first_name = forms.CharField(label="Nome", max_length=150)
    last_name = forms.CharField(label="Apelido", max_length=150, required=False)
    birth_date = forms.DateField(
        label="Data de nascimento",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "birth_date")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Telemóvel"
        self.fields["username"].help_text = "É com este número que vais entrar."
        self.fields["username"].widget.attrs.update(
            {"inputmode": "tel", "placeholder": "9xxxxxxxx"}
        )

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
