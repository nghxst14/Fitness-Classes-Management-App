from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Painel de administração dos utilizadores."""

    # Colunas mostradas na lista de utilizadores
    list_display = (
        "username",
        "get_full_name",
        "email",
        "phone",
        "is_trainer",
        "is_staff",
    )
    list_filter = ("is_trainer", "is_staff", "is_active")
    search_fields = ("username", "first_name", "last_name", "email", "phone")

    # Acrescenta os nossos campos extra aos formulários do utilizador,
    # reaproveitando a estrutura padrão do Django.
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Dados adicionais", {"fields": ("phone", "is_trainer", "created_at")}),
    )
    readonly_fields = ("created_at",)

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Dados adicionais", {"fields": ("phone", "is_trainer")}),
    )

    @admin.display(description="Nome")
    def get_full_name(self, obj):
        return obj.get_full_name()
