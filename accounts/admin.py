from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from .models import User


class BirthdayTodayFilter(admin.SimpleListFilter):
    """Filtro rápido para ver quem faz anos hoje."""

    title = "Aniversário"
    parameter_name = "bday"

    def lookups(self, request, model_admin):
        return [("today", "Faz anos hoje")]

    def queryset(self, request, queryset):
        if self.value() == "today":
            today = timezone.localdate()
            return queryset.filter(
                birth_date__month=today.month, birth_date__day=today.day
            )
        return queryset


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Painel de administração dos utilizadores (login por telemóvel)."""

    class Media:
        # Bolinhas de cor por tipo de crédito nos cabeçalhos das colunas de
        # saldo (iguais às da faixa de saldos do site).
        css = {"all": ("css/admin-saldos.css",)}

    list_display = (
        "username",
        "get_full_name",
        "sessoes_sg",
        "sessoes_pt",
        "sessoes_hybrid",
        "birth_date",
        "is_trainer",
        "is_staff",
    )
    # Permite ao Sérgio atualizar os saldos direto na lista (após pagamento).
    list_editable = ("sessoes_sg", "sessoes_pt", "sessoes_hybrid")
    list_filter = (BirthdayTodayFilter, "is_trainer", "is_staff", "is_active")
    search_fields = ("username", "first_name", "last_name")
    ordering = ("first_name", "last_name", "username")

    def get_actions(self, request):
        # Sem remoção em massa: apagar contas é raro e delicado (histórico de
        # marcações vai atrás) — faz-se uma a uma, na ficha do utilizador,
        # como nas Sessões.
        acoes = super().get_actions(request)
        acoes.pop("delete_selected", None)
        return acoes

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Dados pessoais", {"fields": ("first_name", "last_name", "birth_date")}),
        (
            "Sessões disponíveis",
            {"fields": ("sessoes_sg", "sessoes_pt", "sessoes_hybrid")},
        ),
        # Sem "groups"/"user_permissions": só fariam sentido com vários
        # funcionários no admin (ver nota em bookings/admin.py).
        (
            "Permissões",
            {"fields": ("is_trainer", "is_active", "is_staff", "is_superuser")},
        ),
        ("Datas", {"fields": ("last_login", "date_joined", "created_at")}),
    )
    readonly_fields = ("created_at",)

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
    )

    @admin.display(description="Nome")
    def get_full_name(self, obj):
        return obj.get_full_name()
