"""
Passwords provisórias, para quando um aluno se esquece da sua.

O Sérgio gera uma com um clique na ficha e manda-a pelo WhatsApp. O aluno
entra com ela e é obrigado a escolher outra — a provisória morre no primeiro
uso, e assim o treinador nunca fica a saber a password definitiva de
ninguém.
"""
import secrets

# Sem 0/O, 1/l/I nem 5/S: esta password vai ser ditada ou lida numa mensagem
# de WhatsApp, e um zero confundido com um O é uma tentativa gasta das cinco
# que o travão do login permite.
ALFABETO = "abcdefghjkmnpqrtuvwxyz2346789"

# Seis é o mínimo que o projeto exige (ver AUTH_PASSWORD_VALIDATORS) e o
# suficiente para uma password que dura um login: 29^6 são 594 milhões de
# combinações, contra cinco tentativas antes do bloqueio de 15 minutos.
COMPRIMENTO = 6


def gerar_password_provisoria():
    """Uma password curta, aleatória e sem caracteres que se confundam."""
    return "".join(secrets.choice(ALFABETO) for _ in range(COMPRIMENTO))
