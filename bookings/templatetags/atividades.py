"""
O resumo das últimas ações, para a página de entrada do painel.

Existe para o Sérgio a meio de atualizar os créditos do mês: se não se
lembrar se já deu os da Joana, vê aqui em vez de ir abrir a ficha dela.

Junta **duas** fontes, porque nenhuma delas chega sozinha:

- O registo do painel (`LogEntry`) sabe tudo o que se faz no admin — criar
  um local, mudar uma aula — mas nas alterações de saldo diz só "Foi
  modificado Sessões Small Group", sem o valor. Não responde a "dei-lhe 10
  ou 12?".
- O livro de movimentos (`MovimentoCredito`) tem o valor, mas só sabe de
  créditos.

Então: os créditos vêm do livro (com o valor) e tudo o resto vem do registo
do painel. As alterações de saldo são retiradas do registo para o mesmo
ajuste não aparecer duas vezes.
"""
import json

from django import template
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from bookings.models import MovimentoCredito

register = template.Library()

# Os verbose_name dos três campos de saldo. Uma alteração que mexa SÓ nestes
# é um ajuste de créditos e já vem do livro de movimentos.
CAMPOS_DE_SALDO = {
    "Sessões Small Group", "Sessões PT", "Sessões Hybrid",
}

VERBOS = {ADDITION: "criado", CHANGE: "alterado", DELETION: "apagado"}


def ha_quanto_tempo(quando):
    """
    O tempo decorrido, escrito como uma pessoa o diria.

    O `timesince` do Django não serve aqui por duas razões: o catálogo pt
    não traduz "minutes"/"hours"/"days" (o mesmo buraco que deixa o "View"
    em inglês no painel), e para uma coisa acabada de fazer devolve
    "0 minutes", que não diz nada a ninguém.

    Ao fim de um dia passa a dar a hora em vez de a contagem: "ontem, 14:32"
    lê-se de imediato, "há 26 horas" obriga a fazer contas de cabeça.
    """
    segundos = (timezone.now() - quando).total_seconds()
    if segundos < 60:
        return "agora mesmo"
    if segundos < 3600:
        return f"há {int(segundos // 60)} min"
    if segundos < 86400:
        horas = int(segundos // 3600)
        return f"há {horas} hora{'s' if horas > 1 else ''}"

    local = timezone.localtime(quando)
    dias = (timezone.localdate() - local.date()).days
    if dias == 1:
        return f"ontem, {local:%H:%M}"
    return f"{local:%d/%m, %H:%M}"


def _so_mexeu_em_saldos(registo):
    """O registo do painel diz respeito apenas a campos de saldo?"""
    try:
        alteracoes = json.loads(registo.change_message)
    except (ValueError, TypeError):
        # O Django gravava mensagens em texto livre antes da 1.10, e as
        # ações próprias podem gravar o que quiserem. Na dúvida, mostra-se.
        return False
    if not isinstance(alteracoes, list):
        return False
    campos = set()
    for parte in alteracoes:
        if "changed" not in parte:
            return False
        campos.update(parte["changed"].get("fields", []))
    return bool(campos) and campos <= CAMPOS_DE_SALDO


def _do_livro_de_movimentos(limite):
    """
    Os créditos mexidos à mão pelo Sérgio, com o valor.
    Ex.: "Joana Silva +10 Small Group".

    São dois motivos e não um: somar fica registado como COMPRA (é quase
    sempre um pagamento) e tirar como AJUSTE (é uma correção). Os dois vêm
    do mesmo gesto — ele a editar o saldo na lista — e os dois interessam
    aqui. Os movimentos automáticos (reservas, cancelamentos dos alunos)
    ficam de fora: numa semana movimentada enchiam as cinco linhas e ele
    deixava de ver o que fez.
    """
    ajustes = (
        MovimentoCredito.objects
        .filter(motivo__in=[MovimentoCredito.COMPRA, MovimentoCredito.AJUSTE])
        .select_related("client")[:limite]
    )
    for mov in ajustes:
        sinal = "+" if mov.quantidade >= 0 else "−"
        yield {
            "quando": mov.created_at,
            "ha_quanto": ha_quanto_tempo(mov.created_at),
            "quem": str(mov.client),
            # De propósito sem o saldo final: o que interessa aqui é o que
            # foi dado, não o total (pedido do André, set 2026).
            "detalhe": f"{sinal}{abs(mov.quantidade)} {mov.get_credit_type_display()}",
            "url": f"/admin/accounts/user/{mov.client_id}/change/",
            "tipo": "credito",
        }


def _do_registo_do_painel(limite):
    """Tudo o resto: locais criados, aulas alteradas, pacotes apagados."""
    tipo_utilizador = ContentType.objects.get(app_label="accounts", model="user")
    registos = (
        LogEntry.objects
        .select_related("content_type")
        # Mais do que o limite: alguns vão ser descartados a seguir.
        [: limite * 3]
    )
    for registo in registos:
        if registo.content_type_id == tipo_utilizador.id and _so_mexeu_em_saldos(
            registo
        ):
            continue  # já veio do livro de movimentos, com o valor
        nome = registo.content_type.name if registo.content_type else "registo"
        yield {
            "quando": registo.action_time,
            "ha_quanto": ha_quanto_tempo(registo.action_time),
            "quem": registo.object_repr,
            "detalhe": f"{nome} {VERBOS.get(registo.action_flag, 'alterado')}",
            "url": registo.get_admin_url() if registo.action_flag != DELETION else None,
            "tipo": "painel",
        }


@register.simple_tag
def atividades_recentes(limite=5):
    """As últimas `limite` atividades, das duas fontes, da mais recente para trás."""
    juntas = list(_do_livro_de_movimentos(limite)) + list(
        _do_registo_do_painel(limite)
    )
    juntas.sort(key=lambda a: a["quando"], reverse=True)
    return juntas[:limite]
