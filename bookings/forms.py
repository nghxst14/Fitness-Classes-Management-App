from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class SignUpForm(UserCreationForm):
    """
    Formulário de auto-registo dos alunos.

    Estende o formulário padrão do Django (que trata da password e da sua
    confirmação) e acrescenta nome, email e telemóvel.
    """

    first_name = forms.CharField(label="Nome", max_length=150)
    last_name = forms.CharField(label="Apelido", max_length=150, required=False)
    email = forms.EmailField(label="Email")
    phone = forms.CharField(label="Telemóvel", max_length=20, required=False)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.phone = self.cleaned_data["phone"]
        if commit:
            user.save()
        return user
