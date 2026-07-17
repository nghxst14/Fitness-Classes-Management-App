# CLAUDE.md — Contexto do projeto (RESTART NOW)

> Ficheiro de contexto para o assistente. Lê isto primeiro. Está em português
> porque todo o projeto (UI, comentários, admin) é em português de Portugal.

## O que é

Plataforma web para um **personal trainer / estúdio** (marca **RESTART NOW**,
cliente: **Sérgio**). Substitui a marcação de aulas por WhatsApp por um site
onde os alunos se registam, veem o horário, reservam aulas com um sistema de
**créditos**, e compram pacotes falando com o treinador pelo WhatsApp.

É o **primeiro projeto real** do André (programador júnior). O André está a
aprender ao mesmo tempo — explica as decisões, não despejes código sem contexto.
A prioridade é entregar algo simples e funcional até **início de setembro**
(início da nova época do cliente).

## Stack

- **Django 5** + **templates** (server-rendered, sem React) + um pouco de JS.
- **SQLite** em desenvolvimento; **PostgreSQL** em produção (no deploy, ainda por fazer).
- Sem Docker. Ambiente virtual `venv`. Ver `GUIA_COMANDOS.md` para os comandos.
- Vídeos (quando existiam) eram incorporados de YouTube/Vimeo, nunca alojados.

## Como correr

```powershell
venv\Scripts\activate
python manage.py runserver
```
Migrar só quando os modelos mudam: `makemigrations` + `migrate`.
Detalhes completos em `GUIA_COMANDOS.md`.

## Estrutura

- `config/` — settings, urls, wsgi.
- `accounts/` — modelo de utilizador personalizado (`User`) + login com throttle.
- `bookings/` — o núcleo: locais, tipos de serviço, sessões, reservas, pacotes.
- `templates/`, `static/` — HTML e CSS/JS. Marca em `static/img/brand/`.

## Modelo de negócio e decisões-chave (importante)

Estas decisões vieram de reuniões com o Sérgio e **substituem** ideias antigas:

1. **Login por número de telemóvel**, não email. O número é guardado no campo
   `username` do Django (é o identificador de login). O Sérgio vive no WhatsApp;
   o email não é usado. Formulários relabelam `username` como "Telemóvel"
   (ver `bookings/forms.py`: `SignUpForm`, `PhoneLoginForm`).

2. **Sistema de créditos (tokens).** `User.credits` (inteiro). Cada reserva
   gasta 1 crédito; cancelar devolve 1. Sem créditos, o aluno é enviado para os
   pacotes. **1 crédito = qualquer aula** (todas custam 1). Créditos **não expiram**.

3. **Pacotes vendidos pelo WhatsApp.** Modelo `Pack` (bookings). A página
   `/pacotes/` mostra os pacotes ativos; cada um tem um botão que abre o WhatsApp
   do Sérgio (link `wa.me`) com uma **mensagem pré-preenchida e personalizável**
   por ele no admin (`Pack.whatsapp_message`). A venda/pagamento é tratada
   organicamente por ele fora da app.

4. **Créditos são atribuídos manualmente pelo Sérgio.** Como a compra é fora da
   app, após o pagamento ele vai ao admin (Utilizadores) e edita os `credits` do
   aluno — dá para editar direto na lista (`list_editable`). O histórico fica no
   "History" do próprio objeto no admin.

5. **Recuperação de password = via WhatsApp (Opção A).** NÃO há recuperação por
   email. O link "Esqueci-me da password" no login abre o WhatsApp do Sérgio;
   ele redefine a password do aluno no admin. (Alternativa futura: código por
   SMS via gateway pago — não implementado.)

6. **Horário navegável por dia.** O Sérgio marca a semana toda de uma vez; o
   aluno anda para trás/frente entre dias no `/horario/` (`?date=AAAA-MM-DD`).

7. **Aba de vídeos removida DE TODO** (jul 2026). O cliente decidiu que não é
   necessária. A app `library` foi apagada por completo (código, tabelas,
   admin); se algum dia voltar, recupera-se do histórico do Git.

8. **Data de nascimento no registo** para o Sérgio saber os aniversários.
   Por agora, há um filtro no admin ("Faz anos hoje"). O **aviso automático
   diário** ainda NÃO existe — precisa de tarefa agendada (fazer no deploy).
   Enviar por WhatsApp automaticamente exige a API paga; o realista é um
   lembrete diário ao Sérgio.

## Configuração relevante

- `config/settings.py`:
  - `AUTH_USER_MODEL = "accounts.User"`
  - `LANGUAGE_CODE = "pt-pt"`, `TIME_ZONE = "Europe/Lisbon"`.
  - `AUTH_PASSWORD_VALIDATORS`: só mínimo de 6 caracteres (público pouco técnico).
  - `SERGIO_WHATSAPP = "351939339857"` — **número de TESTE do André**. Trocar
    pelo número do Sérgio em produção (um só sítio, usado em todos os links wa.me).
  - `EMAIL_BACKEND` = console (resquício; o email já não é usado no fluxo).

## Modelos (resumo)

- `accounts.User(AbstractUser)`: + `birth_date`, `credits`, `is_trainer`,
  `created_at`. `username` = telemóvel. Propriedade `phone` devolve o username.
- `bookings.Location`: nome, `kind` (indoor/outdoor), morada, ativo.
- `bookings.ServiceType`: nome, lotação por defeito, `is_online`,
  `min_cancel_hours` (antecedência p/ cancelar), ativo.
- `bookings.Session`: tipo de serviço, treinador, local, início, duração,
  lotação, cancelada. Propriedades: `spots_taken/left`, `is_full`, `is_past`,
  `card_image` (fundo indoor/outdoor conforme o local).
- `bookings.Booking`: sessão + aluno + estado (booked/cancelled/attended/no_show).
  Constraint única (sessão, aluno). Método `client_can_cancel()` aplica a regra
  de antecedência do tipo de serviço; `client_cancellable` (bool p/ template).
- `bookings.Pack`: nome, descrição, `number_of_sessions` (= créditos), preço
  (opcional), `whatsapp_message`, ordem, ativo.
- `bookings.ClientPack`: existe mas **não é central** agora (os créditos vivem no
  User). Não removido para evitar migração destrutiva; escondido do admin.

## Fluxos principais (views em bookings/views.py)

- `home` — antevisão das próximas sessões.
- `signup` — auto-registo por telemóvel; entra logo.
- `schedule` — sessões de um dia + navegação por dia.
- `book` (POST) — valida (não cheia, não passada, tem crédito), cria/reactiva
  reserva, desconta 1 crédito.
- `cancel_booking` (POST) — respeita a regra de antecedência, devolve 1 crédito.
- `my_bookings` — reservas futuras do aluno.
- `packages` — pacotes ativos + link `wa.me` com mensagem preenchida.

Login/logout estão em `config/urls.py` (LoginView com `PhoneLoginForm`), não via
`django.contrib.auth.urls` (a recuperação por email foi removida).

## Marca / visual

- Tema escuro moderno. Paleta em `static/img/brand/MARCA.md`:
  preto `#0F0F0F`, cinza `#202020`, verde vivo `#5DD62C`, verde escuro `#337418`,
  branco `#F8F8F8`. CSS em `static/css/style.css` (variáveis no `:root`).
- Imagens em `static/img/brand/`: `logo-restart-now.png`, `class-outdoor.jpg`,
  `class-indoor.jpg` (fundo dos cartões de aula, escolhido pelo indoor/outdoor).
- Login/registo usam `base_auth.html` (fundo preto, logo centrado, botões verdes).
- Referências de UI (inspiração) em `docs/referencias-ui.md`.

## Estado atual

FEITO: estrutura, modelos, admin PT, registo/login por telemóvel, horário por
dia, reservas com créditos, pacotes com WhatsApp, tema visual RESTART NOW,
recuperação via WhatsApp. Projeto sob Git.

POR FAZER / PRÓXIMOS PASSOS:
1. **Correr as migrações** do último reescopo (User/Pack) se ainda não corridas.
2. **Otimizar as fotos** `class-outdoor.jpg` (~4,6MB) e `class-indoor.jpg` (~1,4MB)
   — redimensionar para ~1600px e comprimir (~200–400KB). Estão demasiado pesadas.
3. **Deploy (Bloco 5)**: Railway ou PythonAnywhere; PostgreSQL; `DEBUG=False`;
   `ALLOWED_HOSTS`; ficheiros estáticos (whitenoise); cache-busting; e a tarefa
   agendada do aniversário. Custo de alojamento ~5–12€/mês, a cargo do cliente
   (a mensalidade de manutenção do André é separada — "Modelo B").
4. **Trocar `SERGIO_WHATSAPP`** para o número real do Sérgio.
5. Afinações visuais e formação do Sérgio (mini-guia do admin).

## Notas / cuidados

- UI, mensagens e admin **sempre em português de Portugal**.
- Manter tudo **simples** — o cliente é pequeno e quer pouca complexidade.
- Sempre que se mexe no CSS, o browser cacheia: usar **Ctrl+F5** para ver mudanças.
- Depois de mexer no código, o fluxo Git é: `git add -A` → `git commit -m "..."`.
- Há ficheiros de templates órfãos (`templates/registration/password_reset_*`,
  `templates/library/*`) que já não têm rota; podem ser apagados, são inofensivos.
