"""Valores das definições que os templates precisam de ver."""
from django.conf import settings


def definicoes(request):
    """
    Expõe o DEBUG aos templates.

    Usado para não registar o service worker em desenvolvimento: em produção
    o WhiteNoise dá nomes com hash aos estáticos (`style.a1b2c3.css`), por
    isso um ficheiro alterado tem endereço novo e a cache do worker nunca
    serve o antigo. Em desenvolvimento não há hash — e o worker passava a
    servir o CSS velho indefinidamente, com o programador a mudar o ficheiro
    e a ver a página na mesma. Aconteceu mesmo, em set 2026.

    O `django.template.context_processors.debug` do Django não serve: só
    define a variável quando o pedido vem de um IP em INTERNAL_IPS.
    """
    return {"DEBUG": settings.DEBUG}
