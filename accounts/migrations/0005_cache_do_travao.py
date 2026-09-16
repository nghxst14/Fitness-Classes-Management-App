"""
Cria a tabela onde vive a contagem de tentativas falhadas do login.

Porquê numa migração e não no `Procfile`: assim a tabela existe em todo o
lado onde o projeto corre — produção, a máquina do André e a base de dados
dos testes — sem ninguém se lembrar de um comando extra. Uma tabela de cache
em falta só dá erro quando alguém tenta entrar, que é o pior momento.
"""
from django.core.management import call_command
from django.db import connection, migrations

NOME_DA_TABELA = "cache_do_travao"  # tem de bater certo com CACHES no settings


def criar(apps, schema_editor):
    # Ao montar a base de dados dos testes, o Django já cria as tabelas de
    # cache sozinho — sem esta verificação o comando avisava que ela já
    # existia e sujava o resultado dos testes com ruído.
    if NOME_DA_TABELA in connection.introspection.table_names():
        return
    call_command("createcachetable", NOME_DA_TABELA, verbosity=0)


def apagar(apps, schema_editor):
    schema_editor.execute(f"DROP TABLE IF EXISTS {NOME_DA_TABELA}")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_user_consentimento_em"),
    ]

    operations = [
        migrations.RunPython(criar, apagar),
    ]
