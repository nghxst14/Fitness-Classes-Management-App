"""
Configurações do projeto Django (Gestão de Treinos).

Documentação: https://docs.djangoproject.com/en/5.0/ref/settings/
"""
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

# Caminho base do projeto (a pasta que contém o manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Segurança ---------------------------------------------------------------
# Em desenvolvimento usamos um valor por defeito. Em produção, definir a
# variável de ambiente DJANGO_SECRET_KEY com um valor secreto e único.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-inseguro-troca-isto-em-producao",
)

# DEBUG deve ser False em produção. Controlado por variável de ambiente.
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost"
).split(",")

# Domínios de confiança para POSTs (admin, formulários) atrás do HTTPS do
# Railway. Em produção, definir DJANGO_CSRF_TRUSTED_ORIGINS com o domínio
# (ex.: "https://o-meu-site.up.railway.app").
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o
]


# --- Aplicações --------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # As nossas apps:
    "accounts",
    "bookings",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serve os ficheiros estáticos em produção (logo a seguir ao
    # SecurityMiddleware, como manda a documentação). Em dev é inofensivo.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- Base de dados -----------------------------------------------------------
# Produção: PostgreSQL, lido da variável DATABASE_URL que o Railway injeta.
# Desenvolvimento: SQLite (um ficheiro, sem instalação nenhuma).
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# --- Validação de palavras-passe ---------------------------------------------
# Optámos por regras simples (público com menos à-vontade tecnológico):
# apenas um mínimo de 6 caracteres. Sem exigir maiúsculas, símbolos, etc.
# Como as contas não guardam dados sensíveis nem pagamentos, o risco é baixo
# — e o login tem limite de tentativas (accounts.views.ThrottledLoginView).
# Quem esquece a password fala com o Sérgio pelo WhatsApp e ele redefine-a
# no admin.
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
]


# --- Internacionalização (Portugal) ------------------------------------------
LANGUAGE_CODE = "pt-pt"
TIME_ZONE = "Europe/Lisbon"
USE_I18N = True
USE_TZ = True


# --- Ficheiros estáticos (CSS, JS, imagens) ----------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Ficheiros carregados (ex.: logótipo).
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Em produção, o WhiteNoise serve os estáticos comprimidos e com hash no nome
# (cache-busting automático). Só quando DEBUG=False: em dev, o Django serve os
# ficheiros diretamente e não há `collectstatic` corrido.
if not DEBUG:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }


# --- Modelo de utilizador personalizado --------------------------------------
# Definimos isto logo no início do projeto (boa prática): permite-nos
# acrescentar campos ao utilizador (ex.: telemóvel) sem dores de cabeça depois.
AUTH_USER_MODEL = "accounts.User"

# Para onde enviar o utilizador depois do login/logout:
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGIN_URL = "login"


# --- WhatsApp -----------------------------------------------------------------
# Número (com indicativo, sem "+" nem espaços) para os links wa.me dos pacotes
# e da ajuda com a password. Em produção, definir a variável SERGIO_WHATSAPP
# com o número real do Sérgio. O default é o número de TESTE do André.
SERGIO_WHATSAPP = os.environ.get("SERGIO_WHATSAPP", "351939339857")

# Em produção o número TEM de vir do ambiente. O valor por omissão é o número
# de TESTE do André: se a variável for esquecida ou escrita com erro no
# Railway, a app não falha — sobe alegremente e manda TODOS os alunos falar
# com a pessoa errada, em silêncio. É o pior tipo de erro: não dá sinal
# nenhum. Mais vale a app recusar arrancar.
if not DEBUG and not os.environ.get("SERGIO_WHATSAPP"):
    raise ImproperlyConfigured(
        "Falta a variável de ambiente SERGIO_WHATSAPP com o número real do "
        "Sérgio (indicativo + número, sem '+' nem espaços). Sem ela, os "
        "botões dos pacotes mandariam os alunos para o número de teste."
    )


# --- RGPD (política de privacidade) ------------------------------------------
# Quem responde legalmente pelos dados dos alunos é o SÉRGIO (o negócio é
# dele), não quem fez a app. Estes três valores são o que a política precisa
# de dizer e só ele pode fornecer: como se identifica, para onde se escreve a
# pedir os dados ou o apagamento, e quanto tempo os guarda depois de alguém
# deixar de ser aluno.
RGPD_RESPONSAVEL = os.environ.get("RGPD_RESPONSAVEL", "")
RGPD_CONTACTO = os.environ.get("RGPD_CONTACTO", "")
RGPD_PRAZO_ANOS = os.environ.get("RGPD_PRAZO_ANOS", "")

# Mesma lógica do SERGIO_WHATSAPP: em produção isto não pode ficar por
# preencher. Uma política publicada sem responsável nem contacto não é uma
# política — é um texto que finge ser uma. Vazio em dev mostra um aviso na
# própria página, para não passar despercebido.
if not DEBUG and not all([RGPD_RESPONSAVEL, RGPD_CONTACTO, RGPD_PRAZO_ANOS]):
    raise ImproperlyConfigured(
        "Faltam dados da política de privacidade: RGPD_RESPONSAVEL (nome ou "
        "entidade do Sérgio), RGPD_CONTACTO (email ou telemóvel para pedidos "
        "sobre dados) e RGPD_PRAZO_ANOS (anos que guarda os dados de quem "
        "deixa de ser aluno). Sem eles a página de privacidade fica por "
        "preencher e os alunos não têm a quem se dirigir."
    )


# --- Segurança em produção ---------------------------------------------------
# Só quando DEBUG=False. O Railway serve tudo por HTTPS atrás de um proxy;
# estas opções dizem ao Django para confiar no cabeçalho do proxy e forçar
# ligações seguras (cookies só por HTTPS, redirecionar HTTP->HTTPS, HSTS).
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 dias
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# --- Registo de erros ---------------------------------------------------------
# Sem isto, um erro 500 em produção mostra a página de erro ao aluno e não
# deixa rasto nenhum: só ficarias a saber quando o Sérgio telefonasse, dias
# depois. Escrever para a consola é de propósito — o Railway capta o que a app
# escreve e mostra-o no separador "Logs", sem ser preciso instalar nada.
#
# Se um dia quiseres ser avisado (email/telemóvel) em vez de teres de ir lá
# ver, o passo seguinte é ligar o Sentry, que tem um plano gratuito mais do
# que suficiente para esta escala.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simples": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "consola": {
            "class": "logging.StreamHandler",
            "formatter": "simples",
        },
    },
    "root": {"handlers": ["consola"], "level": "INFO"},
    "loggers": {
        # Os erros 500 passam por aqui. O propagate=False evita a linha
        # duplicada (uma do logger, outra da raiz).
        "django.request": {
            "handlers": ["consola"],
            "level": "ERROR",
            "propagate": False,
        },
        # Em desenvolvimento, o Django regista cada query em DEBUG: seria
        # ruído a esconder o que interessa.
        "django.db.backends": {"level": "WARNING"},
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
