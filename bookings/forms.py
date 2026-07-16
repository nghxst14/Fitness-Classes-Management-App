from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


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
