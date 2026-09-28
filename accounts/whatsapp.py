"""
O número de um aluno como link para abrir a conversa no WhatsApp.

Vive aqui e não no admin das marcações porque o telemóvel é do utilizador, e
são três os sítios do painel que precisam disto: a ficha e a lista de
Utilizadores, as Marcações, e a Lista de espera. Estava escrito duas vezes,
o que é o costume antes de uma das cópias divergir.

O WhatsApp é o canal deste negócio: o pagamento, os avisos e a recuperação
de password passam todos por lá. Copiar um número à mão para o procurar no
telemóvel é o tipo de atrito que faz com que o aviso não chegue a ser dado.
"""
import re

from django.templatetags.static import static
from django.utils.html import format_html

# O formato que este projeto usa em todo o lado: 9 dígitos a começar por 9.
# Contas de staff ("admin", "chefe") não passam neste crivo e ficam sem link
# — não há conversa de WhatsApp para abrir com elas.
TELEMOVEL_PT = re.compile(r"9\d{8}")


def icone_whatsapp(utilizador, titulo="Abrir conversa no WhatsApp"):
    """
    O mesmo link, mas como ícone — para tabelas onde o espaço é escasso.

    A lista de Utilizadores tem dez colunas; a palavra "conversar" gastava
    largura para dizer o que o símbolo do WhatsApp diz de relance. E ali o
    número já está na coluna do lado.

    O `alt` não é decoração: sem ele o botão é invisível para quem usa um
    leitor de ecrã, e passaria a haver uma ação sem nome nenhum.
    """
    numero = utilizador.username
    if not TELEMOVEL_PT.fullmatch(numero):
        return ""
    nome = utilizador.get_full_name() or numero
    return format_html(
        '<a href="https://wa.me/351{}" target="_blank" rel="noopener" '
        'data-nome="{}" title="{}" '
        "onclick=\"return confirm('{} com ' + this.dataset.nome + '?')\">"
        '<img src="{}" alt="{}" width="18" height="18" '
        'style="vertical-align:middle;"></a>',
        numero, nome, titulo, titulo, static("img/whatsapp.svg"), titulo,
    )


def link_whatsapp(
    utilizador, texto_do_confirm="Abrir conversa no WhatsApp com", etiqueta=None
):
    """
    Devolve o link, ou só o número quando não há conversa possível.

    Por omissão o link mostra o número, que é o que serve nas Marcações e na
    Lista de espera — lá a coluna do lado tem o nome. Nos Utilizadores o
    nome de conta já É o telemóvel, e repeti-lo não acrescentava nada: essas
    passam uma `etiqueta` a dizer o que o link faz.

    Pede confirmação antes de abrir: no meio de uma lista, um clique a mais
    abriria uma conversa com a pessoa errada.

    O nome vai num atributo `data-` e é lido em runtime com
    `this.dataset.nome` — **nunca** interpolado dentro do JS do onclick.
    Interpolar aí permitia XSS: o browser desfaz o escape de HTML no
    contexto do atributo, e um nome com aspas partia a string do confirm e
    injetava código no painel. Já aconteceu uma vez, na coluna das Marcações.
    """
    numero = utilizador.username
    if not TELEMOVEL_PT.fullmatch(numero):
        return numero
    nome = utilizador.get_full_name() or numero
    return format_html(
        '<a href="https://wa.me/351{}" target="_blank" rel="noopener" '
        'data-nome="{}" '
        "onclick=\"return confirm('{} ' + this.dataset.nome + '?')\">{}</a>",
        numero, nome, texto_do_confirm, etiqueta or numero,
    )
