# Gestão de Treinos — web app (Django)

Plataforma (marca **RESTART NOW**) para o aluno se registar, ver o horário e
reservar aulas gastando créditos; os créditos compram-se em pacotes negociados
pelo WhatsApp. Substitui a marcação por WhatsApp por algo centralizado.

> Contexto completo do projeto (ao pormenor) em **`CLAUDE.md`**.

Stack: **Django 5 + templates + SQLite** (em desenvolvimento).
Em produção passaremos para PostgreSQL (Bloco 5).

---

## Como pôr a correr (primeira vez)

> Precisas de ter o **Python 3.10+** instalado. Confirma com `python --version`.

Abre um terminal (PowerShell) **dentro desta pasta** e corre, por ordem:

```powershell
# 1. Criar um ambiente virtual (isola as dependências do projeto)
python -m venv venv

# 2. Ativar o ambiente virtual
venv\Scripts\activate
# (No Mac/Linux seria:  source venv/bin/activate)

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Criar a base de dados a partir dos modelos
python manage.py makemigrations
python manage.py migrate

# 5. Criar a tua conta de administrador (o login do Sérgio/teu)
python manage.py createsuperuser

# 6. Arrancar o servidor de desenvolvimento
python manage.py runserver
```

Depois abre o browser em **http://127.0.0.1:8000/admin/** e entra com a conta
que criaste no passo 5.

### Nas próximas vezes

Só precisas de ativar o ambiente e arrancar:

```powershell
venv\Scripts\activate
python manage.py runserver
```

---

## O que já existe (Bloco 1)

O **painel de administração** (`/admin/`) com tudo o que o Sérgio precisa de gerir:

- **Utilizadores** — alunos e treinadores (com telemóvel e a marca "é treinador").
- **Locais** — indoor / outdoor.
- **Tipos de serviço** — Aula de Grupo, PT Individual, Small Group, Plano Online…
  (cada um com uma lotação por defeito).
- **Sessões** — cada aula/treino agendado, com dia, hora, local, lotação e a
  contagem automática de vagas ocupadas/livres.
- **Packs** e **Packs dos alunos** — produtos de packs e o saldo de cada aluno.
- **Marcações** — quem está inscrito em cada sessão.
- **Vídeos** e **Categorias de vídeo** — biblioteca (vídeos do YouTube/Vimeo).

## Bloco 2 — marcações dos alunos (feito)

Já existe a parte visível para os alunos:

- **Registo e login** — o aluno cria a própria conta (`/registar/`) e entra.
- **Horário** (`/horario/`) — lista as sessões futuras com vagas e botão "Marcar".
- **As minhas marcações** (`/as-minhas-marcacoes/`) — ver e cancelar.
- **Regra de cancelamento** — configurável por tipo de serviço no campo
  *Antecedência mínima para cancelar (horas)*: põe **12** no PT/individual e
  deixa **0** nas aulas de grupo. O Sérgio (admin) cancela sempre pelo painel.

> ⚠️ **Como este bloco acrescentou um campo novo** (`min_cancel_hours`), tens de
> voltar a correr as migrações:
>
> ```powershell
> python manage.py makemigrations
> python manage.py migrate
> ```
>
> Depois, no admin, cria alguns **Tipos de serviço**, **Locais** e **Sessões**
> para veres o horário a funcionar. Nos tipos individuais, mete 12 no campo de
> cancelamento.

## Bloco 3 — biblioteca de vídeos (feito)

- **Vídeos** (`/videos/`) — lista os vídeos publicados, agrupados por categoria.
  Acesso: qualquer aluno com sessão iniciada.
- **Página do vídeo** (`/videos/<id>/`) — leitor incorporado (YouTube/Vimeo),
  responsivo, com descrição.

> Não é preciso migração (os modelos de vídeo já existiam do Bloco 1).
>
> Para adicionares um vídeo no admin:
> 1. **Categorias de vídeo → Adicionar** (ex.: "Mobilidade").
> 2. **Vídeos → Adicionar**: título, categoria, plataforma (YouTube/Vimeo) e o
>    **ID do vídeo** — só o identificador, não o link inteiro:
>    - YouTube: em `youtube.com/watch?v=ABC123` → ID = `ABC123`
>    - Vimeo: em `vimeo.com/123456789` → ID = `123456789`
> 3. Marca "Publicado" e grava. Abre `/videos/` para ver.

## Bloco 4 — acabamentos (em curso)

- **Esqueci-me da password** (feito) — fluxo completo de recuperação por email.
  Em desenvolvimento, o email com o link é "enviado" para o **terminal** onde
  corre o `runserver` (não é preciso servidor de email).

  Como testar:
  1. Garante que a conta tem **email** preenchido (as contas de aluno têm; se a
     tua de admin não tiver, define um em *Utilizadores*).
  2. Na página de login, clica em **"Esqueci-me da password"** e mete o email.
  3. Olha para a janela do `runserver`: vais ver o email impresso, com um link
     tipo `http://127.0.0.1:8000/conta/reset/...`.
  4. Abre esse link no browser, define a nova password e entra.

- **Marca (nome/logótipo)** — pendente: personalizamos quando o André recolher
  as infos do cliente.

## O que vem a seguir

- **Bloco 4 (resto)** — logótipo/nome do Sérgio e afinação visual final.
- **Bloco 5** — deploy (pôr online) com PostgreSQL e email real.

---

## Mapa dos modelos de dados

```
User (accounts)
 └─ alunos e treinadores

Location ─┐
ServiceType ─┼─> Session ──< Booking >── User (aluno)
            │        (uma aula/treino     (inscrição)
            │         agendado)
Pack ──> ClientPack ──> (saldo de sessões do aluno)

VideoCategory ──< Video   (biblioteca; vídeos no YouTube/Vimeo)
```

- Um `ServiceType` define *que tipo* de serviço é (e a lotação sugerida).
- Uma `Session` é uma ocorrência concreta na agenda.
- Uma `Booking` liga um aluno a uma sessão (com estado: marcada, cancelada…).
- Um `Pack` é o produto; um `ClientPack` é o pack que um aluno comprou e o seu saldo.
```
