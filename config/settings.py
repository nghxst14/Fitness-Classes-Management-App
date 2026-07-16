"""
Configurações do projeto Django (Gestão de Treinos).

Documentação: https://docs.djangoproject.com/en/5.0/ref/settings/
"""
import os
from pathlib import Path

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
    "library",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
# Em desenvolvimento usamos SQLite (um ficheiro, sem instalação nenhuma).
# Em produção passaremos para PostgreSQL no Bloco 5 (deploy).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# --- Validação de palavras-passe ---------------------------------------------
# Optámos por regras simples (público com menos à-vontade tecnológico):
# apenas um mínimo de 6 caracteres. Sem exigir maiúsculas, símbolos, etc.
# Como as contas não guardam dados sensíveis nem pagamentos, o risco é baixo.
# Nota: a melhor ajuda a quem esquece a password será o "Esqueci-me da
# password" por email, que fica para os acabamentos (Bloco 4).
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

# Ficheiros carregados (ex.: logótipo). Para vídeos usaremos YouTube/Vimeo.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"


# --- Modelo de utilizador personalizado --------------------------------------
# Definimos isto logo no início do projeto (boa prática): permite-nos
# acrescentar campos ao utilizador (ex.: telemóvel) sem dores de cabeça depois.
AUTH_USER_MODEL = "accounts.User"

# Para onde enviar o utilizador depois do login/logout:
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGIN_URL = "login"


# --- Email -------------------------------------------------------------------
# Em desenvolvimento, os emails (ex.: link de recuperação de password) são
# "enviados" para o terminal onde corre o runserver — não é preciso servidor
# de email nenhum para testar. No deploy (Bloco 5) ligamos a um email real.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "Gestão de Treinos <nao-responder@exemplo.pt>"

# --- WhatsApp -----------------------------------------------------------------
# Número (com indicativo, sem "+" nem espaços) para os links wa.me dos pacotes
# e da ajuda com a password. TROCAR pelo número do Sérgio quando for para produção.
SERGIO_WHATSAPP = "351939339857"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
