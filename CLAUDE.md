# CLAUDE.md — Contexto do projeto (RESTART NOW)

> Ficheiro de contexto para qualquer assistente de IA. **Lê isto primeiro.**
> Está em português de Portugal porque **todo** o projeto (UI, mensagens,
> admin, comentários de código) é em pt-PT. Mantém tudo em pt-PT.
>
> Outros documentos no repositório: `GUIA_COMANDOS.md` (comandos passo a passo
> para o André), `PENDENTES.md` (decisões à espera do cliente), `README.md`
> (arranque), `static/img/brand/MARCA.md` (paleta), `docs/referencias-ui.md`
> (inspiração visual).

---

## 1. O que é

Plataforma web para um **personal trainer / estúdio** — marca **RESTART NOW**,
cliente **Sérgio**. Substitui a marcação de aulas por WhatsApp por um site onde
os alunos se registam, veem o horário, e **reservam aulas gastando créditos**.
Os créditos compram-se em **pacotes**, negociados com o treinador pelo WhatsApp
(o pagamento é tratado por ele, fora da app).

É o **primeiro projeto real** do André (programador júnior, a aprender). Ao
trabalhar com ele: **explica as decisões, não despejes código sem contexto**,
e quando ele pede uma explicação para decidir algo, **explica e espera** — não
executes logo. Prioridade: entregar algo **simples e funcional**.

**Sobre o prazo:** a meta era "início de setembro de 2026" (nova época do
cliente). Essa data passou e o André confirmou (set 2026) que **não há prazo
rígido** — o objetivo passou a ser chegar a um produto acabado e polido, sem
pressa artificial. Isso **não** revoga a simplicidade: manter tudo simples
continua a ser requisito do cliente, não um acaso. O que mudou foi haver
espaço para fazer bem, não licença para complicar.

---

## 2. Stack e como correr

- **Django 5.1** + templates server-rendered (sem React) + JS mínimo (vanilla).
- **SQLite** em desenvolvimento; **PostgreSQL** em produção (deploy por fazer).
- Sem Docker. Ambiente virtual `venv/`. Windows + PowerShell.
- **Python 3.12** (é o que o `.python-version` declara e o que o Railway vai
  usar — manter alinhado). As dependências do `requirements.txt` instalam-se
  **todas**, inclusive as de produção: o `settings.py` importa o
  `dj_database_url` no topo, por isso ele é obrigatório mesmo em dev. O
  gunicorn instala mas não corre no Windows — só é usado em produção.

```powershell
venv\Scripts\activate
python manage.py runserver          # http://127.0.0.1:8000/  (site) e /admin/
python manage.py test accounts bookings   # 153 testes, todos a passar
python -m ruff check .                    # linter (configurado no pyproject.toml)
```
As ferramentas de desenvolvimento (o **ruff**) estão no `requirements-dev.txt`,
não no `requirements.txt` — a app não precisa delas para correr e o Railway não
as deve instalar. **A cada push, o GitHub Actions corre o linter, o `check`, os
testes e o `makemigrations --check`** (`.github/workflows/testes.yml`): um push
que parta alguma coisa fica com uma cruz vermelha em vez de passar despercebido
até ao deploy.
`makemigrations` + `migrate` só quando os modelos mudam. Ao mexer no CSS, o
browser cacheia — usar **Ctrl+F5**. Detalhes completos em `GUIA_COMANDOS.md`.

**O `venv/` não é portátil** e parte-se sem avisar (aponta para o caminho
absoluto do Python que o criou). Se o projeto mudar de máquina ou de perfil de
utilizador, é preciso recriá-lo — ver `GUIA_COMANDOS.md`.

**Há mais do que um Python nesta máquina** (set 2026): o 3.12 para este
projeto e o **3.14** para tudo o resto, que é o que o `python` solto aponta.
Recriar o venv tem de ser sempre com **`py -3.12 -m venv venv`** — com
`python` ficaria um venv 3.14, desalinhado do `.python-version` e da produção,
e o Django 5.1 só suporta oficialmente até ao 3.13. Confirmar com
`.\venv\Scripts\python.exe --version` (tem de dizer 3.12.x).

**Mostrar o site a alguém de fora:** `.\scripts\demonstracao.ps1` levanta um
endereço público temporário (túnel Cloudflare) com as definições de produção.
O endereço é sorteado a cada arranque e morre com o script — serve para uma
sessão de demonstração, não para o Sérgio ir usando. Ver `GUIA_COMANDOS.md`.

**Git/GitHub:** o repositório está ligado a
`github.com/nghxst14/Fitness-Classes-Management-App` (privado, via `gh` CLI).
Fluxo por commit: `git add -A` → `git commit` → `git push`. O assistente faz
estes passos pelo André. **Nota PowerShell 5.1:** aspas duplas na mensagem de
commit partem o parser — escrever mensagens sem aspas duplas.

---

## 3. Estrutura do repositório

- `config/` — `settings.py`, `urls.py`, `wsgi.py` (projeto Django "config").
- `accounts/` — app do utilizador:
  - `models.py` — `User` (AbstractUser) + enum `CreditType`.
  - `views.py` — `ThrottledLoginView` (login com limite de tentativas).
  - `admin.py` — admin dos Utilizadores + filtro "Faz anos hoje".
  - `tests.py` — testes do throttle de login.
- `bookings/` — o núcleo do negócio:
  - `models.py` — `Location`, `ServiceType`, `Session`, `MovimentoCredito`,
    `Pack`, `WeeklyProgramSlot`, `Booking` + sinal `pre_delete` de reembolso.
  - `views.py` — páginas do site (home, signup, schedule, book, my_bookings,
    cancel_booking, packages).
  - `forms.py` — `SignUpForm`, `PhoneLoginForm`, `normalizar_telemovel()`.
  - `admin.py` — **muita** personalização (ver secção 7).
  - `urls.py` — rotas das páginas do site.
  - `tests.py` — a maioria dos testes.
  - `templates/admin/widgets/` — templates dos widgets de admin (têm de estar
    numa pasta `templates/` de app, não na de projeto).
- `templates/` — HTML do site (`base.html`, `base_auth.html`, `home.html`,
  `schedule.html`, `packages.html`, `my_bookings.html`, `registration/*`),
  `partials/meta.html` (etiquetas de partilha e favicon, partilhado pelos dois
  templates base) e overrides do admin (`templates/admin/*`).
- `static/` — `css/style.css` (tema do site), `css/admin-extra.css`
  (correções de responsividade do painel), imagens da marca em
  `static/img/brand/` (inclui `favicon.png`).
- `scripts/demonstracao.ps1` — levanta o site num endereço público temporário
  para alguém de fora o ver (ver secção 2).

---

## 4. Modelo de negócio e decisões-chave

Estas decisões vieram de reuniões com o Sérgio e **substituem** ideias antigas.

1. **Login por número de telemóvel**, não email. O número guarda-se no campo
   `username` do Django (é o identificador de login). O Sérgio vive no WhatsApp;
   o email não é usado em lado nenhum. Os formulários relabelam `username` como
   "Telemóvel". Há **normalização**: "912 345 678", "+351912345678" e
   "912345678" viram todos `912345678` (`normalizar_telemovel` em `forms.py`).
   O registo valida o formato (9 dígitos a começar por 9) e recusa duplicados;
   o login **só normaliza** (para não bloquear contas de staff como "admin").

2. **Créditos por TIPO** (decisão de jul 2026 — antes eram genéricos). Há 3
   categorias em `accounts.models.CreditType`: **Small Group (`sg`)**,
   **PT (`pt`)**, **Hybrid (`hybrid`)**. Cada aluno tem **3 saldos**:
   `User.sessoes_sg / sessoes_pt / sessoes_hybrid`. Cada aula declara o seu tipo
   em `ServiceType.credit_type`; reservar gasta 1 do balde correspondente e
   cancelar/apagar devolve **ao mesmo balde**. Um crédito SG **não** paga uma
   aula PT. Cada `Pack` também tem `credit_type` (que balde enche). Créditos
   **não expiram**. O valor curto do tipo é o sufixo do campo
   (`CreditType.SMALL_GROUP` → `sessoes_sg`); `User.campo_saldo(tipo)`,
   `creditos_de(tipo)` e `saldos_creditos()` fazem a ponte.

3. **Pacotes vendidos pelo WhatsApp.** A página `/pacotes/` mostra os `Pack`
   ativos; cada cartão tem um botão que abre o WhatsApp do Sérgio (`wa.me`) com
   uma **mensagem pré-preenchida** (`Pack.whatsapp_message`, ou uma genérica se
   vazia). A venda/pagamento é tratada por ele fora da app.

4. **Créditos atribuídos manualmente pelo Sérgio.** Após o pagamento, ele vai
   ao admin → Utilizadores e edita os 3 saldos (editáveis direto na lista via
   `list_editable`). Cada ajuste fica registado no **livro de movimentos**
   (`MovimentoCredito`) com o valor, o motivo e quem o fez — o "History" do
   admin não serve para isto: só diz que o campo mexeu, nunca de quanto para
   quanto, e não apanha de todo as alterações automáticas.

5. **Recuperação de password = via WhatsApp.** NÃO há reset por email. O link
   "Esqueci-me da password" no login abre o WhatsApp do Sérgio (constante
   `WA_HELP_URL` em `config/urls.py`); ele redefine a password no admin.

6. **Horário navegável por dia** (`/horario/?date=AAAA-MM-DD`). Janela limitada:
   **3 dias para trás** e **14 para a frente** (a view fixa o dia à janela mesmo
   por URL manual; a seta do limite fica visível mas inerte). Para não marcar
   aula a aula, há o **Programa semanal** (`WeeklyProgramSlot`): encaixes fixos
   (dia da semana + hora + tipo + local por defeito) e um botão no admin
   **"Gerar aulas da semana"** que cria as sessões de uma semana de uma vez.
   É **idempotente** (não duplica: salta as que já existem **no mesmo
   instante**) e gera em **hora de Lisboa** (DST-safe). O horário é o que é
   fixo; tipo/local variam por semana e **ajustam-se na própria página de
   gerar, antes de criar as aulas** — o encaixe fica intacto. A exceção
   pontual, depois de gerada, corrige-se na lista de Sessões. Ver a secção 7.

7. **Aba de vídeos removida DE TODO** (jul 2026). A app `library` foi apagada
   por completo (código, tabelas, migração revertida com `migrate library zero`,
   admin). Se voltar, recupera-se do histórico do Git. *(O README ainda pode
   referir vídeos — está desatualizado nesse ponto.)*

8. **Data de nascimento no registo** para o Sérgio saber os aniversários. Há um
   filtro no admin ("Faz anos hoje"). O **aviso automático diário foi
   descartado** (decisão do cliente) — fica só o filtro manual. (Ver
   "Decisões fechadas" no fim da secção 11.)

---

## 5. Modelos de dados (detalhe)

**`accounts.User(AbstractUser)`** — `username` = telemóvel. Campos extra:
`birth_date`, `sessoes_sg`, `sessoes_pt`, `sessoes_hybrid`, `is_trainer`,
`created_at`, `consentimento_em` (quando aceitou a política de privacidade,
no registo — é a prova exigida pelo RGPD; vazio nas contas criadas no admin). Propriedade `phone` (= username); helpers `campo_saldo(tipo)`,
`creditos_de(tipo)`, `saldos_creditos()`. `__str__` = nome completo ou username.

**`bookings.Location`** — `name`, `kind` (`indoor`/`outdoor`), `address`,
`active`. Usado para escolher a imagem do cartão da aula.

**`bookings.ServiceType`** — o "tipo de aula" que o Sérgio cria no admin:
`name`, `description`, **`credit_type`** (SG/PT/Hybrid — que balde a aula gasta),
`default_capacity`, `is_online`, `min_cancel_hours` (antecedência p/ o aluno
cancelar sozinho; 0 = sem restrição), `active`.

**`bookings.Session`** — uma aula concreta na agenda:
`service_type` (FK, PROTECT), `trainer` (FK User, SET_NULL — **escondido do
admin, só há o Sérgio**), `location` (FK, SET_NULL, vazio = online), `title`
(opcional), `start` (DateTimeField), `duration_minutes`, `capacity`,
`is_cancelled`, `notes`, `created_at`. Propriedades: `end`, `spots_taken`,
`spots_left`, `is_full`, `is_past`, **`credit_type`** (vem do service_type),
**`card_image`** (outdoor→`class-outdoor.jpg`, indoor→`class-indoor.jpg`, sem
local→`class-online.jpg`). No `save()`, quando passa de ativa→cancelada, chama
`_refund_active_bookings()` que cancela as marcações ativas e devolve 1 crédito
**ao balde certo** de cada aluno.

**`bookings.MovimentoCredito`** — o **extrato dos créditos**: uma linha por
cada alteração de saldo (`client`, `credit_type`, `quantidade` com sinal,
`motivo`, `saldo_depois`, `session`, `feito_por`, `created_at`). O saldo
continua no `User` porque é rápido de ler; este livro vive ao lado como a
verdade auditável — se algum dia discordarem, o livro é que manda, e a
discordância é o sinal de que algo correu mal. Registado nos **cinco** sítios
que mexem em saldos: `book()`, `cancel_booking()`, `_refund_active_bookings()`,
o sinal `pre_delete`, e o `save_model()` do `UserAdmin` (o ajuste manual do
Sérgio, que é por onde entra o dinheiro). Sempre **dentro da transação que
alterou o saldo**, para não haver como ficar um sem o outro. No admin é
**só de leitura** — um livro que se pode editar não resolve discussões.

**`bookings.ListaEspera`** — a fila de quem quer entrar numa aula cheia
(`session`, `client`, `estado`, `created_at`, `inscrito_em`, `avisado_em`).
Entrar na fila **não** gasta créditos; a ordem da fila é a ordem de chegada
(`ordering = ["created_at"]`). Quando abre vaga,
`promover_da_lista_de_espera(session)` faz subir o primeiro **com saldo** —
quem não tem é saltado e **fica** na fila (a vaga não pode ficar por ocupar,
e tirá-lo seria castigá-lo por estar sem créditos). Chamada dentro da
transação que libertou a vaga, no `cancel_booking`. Quem sobe fica
`INSCRITO` com `avisado_em` vazio: é o que alimenta o ecrã de avisos do
Sérgio (secção 7), porque **a app não avisa ninguém sozinha**.

**`bookings.Pack`** — produto de créditos: `name`, `description`,
**`credit_type`**, `number_of_sessions` (= créditos que dá), `price` (opcional),
`whatsapp_message`, `order`, `active`.

**`bookings.WeeklyProgramSlot`** — encaixe do programa semanal: `weekday`
(0=Segunda … 6=Domingo), `start_time`, `service_type` (por defeito), `location`
(por defeito), `capacity` (vazio = usa a do service_type), `duration_minutes`,
`active`. Métodos: `instante(data)` (o início em hora de Lisboa),
`valores_por_defeito()` (tipo/local/lotação do encaixe) e
`criar_sessao(data, **ajustes)`, que cria a `Session` nessa data — os
`ajustes` substituem os valores por defeito **só naquela criação**, sem
alterar o encaixe. A verificação de duplicados compara **só o instante**
(ver "Decisões fechadas" no `PENDENTES.md`: duas aulas diferentes à mesma
hora não são possíveis, por opção).

**`bookings.Booking`** — marcação: `session` (FK CASCADE), `client` (FK CASCADE),
`status` (`booked`/`cancelled`/`attended`/`no_show`), `client_pack` (FK legado,
não usado), `created_at`. Constraint única `(session, client)`.
`client_can_cancel()` aplica a regra de antecedência do tipo de serviço;
`client_cancellable` é a versão booleana p/ template.
Sinal **`pre_delete`** `devolver_credito_ao_apagar_marcacao`: se uma marcação
**ativa** de uma sessão **futura não-cancelada** for apagada (ex.: o Sérgio
apaga a sessão e as marcações vão em cascata), devolve 1 crédito ao balde certo.
Cobre o caso em que apagar (em vez de cancelar) faria os créditos desaparecerem.

*(O modelo `ClientPack` foi apagado de todo em jul 2026 — era o desenho antigo
em que o saldo vivia no pack comprado; hoje o saldo são os 3 campos do User.)*

---

## 6. Fluxos do site (views em `bookings/views.py`)

Rotas em `bookings/urls.py`; login/logout em `config/urls.py`.

- `home` (`/`) — antevisão das próximas 6 sessões futuras não canceladas.
- `signup` (`/registar/`) — auto-registo por telemóvel; faz login logo.
- `schedule` (`/horario/`, login) — sessões de um dia + navegação por dia
  (limitada a −3/+14 dias); passa `has_prev`/`has_next` ao template. O cartão
  tem quatro estados, e a **ordem no template importa**: `is_past`
  ("Já decorreu", cartão esbatido) é testado **antes** de "Reservado", senão
  uma aula passada a que o aluno foi continuava a mostrar-se como reserva
  ativa.
- `book` (`/marcar/<id>/`, POST, login) — dentro de `transaction.atomic()` com
  `select_for_update()` na sessão: valida (não cancelada, não passada, não
  duplicada, não cheia), **desconta 1 do balde do tipo da aula** com UPDATE
  condicional (`F()`), cria/reactiva a `Booking`. Sem saldo → redireciona para
  `/pacotes/` com mensagem do tipo em falta.
- `my_bookings` (`/as-minhas-marcacoes/`, login) — reservas futuras do aluno.
- `cancel_booking` (`/cancelar/<id>/`, POST, login) — respeita a antecedência,
  cancela com UPDATE condicional (evita devolver 2× em duplo-clique) e devolve
  1 crédito ao balde certo.
- `packages` (`/pacotes/`, login) — packs ativos + link `wa.me` preenchido.
- `entrar_lista_espera` / `sair_lista_espera` (POST, login) — a fila das
  aulas cheias. Ambas voltam ao horário **no dia da aula** (`_voltar_ao_horario`):
  o horário abre sempre em hoje, e sem isso o aluno entrava na fila de uma
  aula de quinta e ficava a olhar para "não há sessões marcadas para este dia".
- `schedule_semana` (`/horario/semana/`, login) — sete dias a partir do dia
  pedido, e **não** de segunda a domingo: a meio da semana, uma grelha fixa
  gastaria metade do ecrã com dias já passados. Agrupa em memória (uma
  consulta só) e usa os mesmos limites do dia a dia, partilhados em
  `_janela_do_horario()` — dois sítios a decidir a mesma coisa acabariam por
  discordar. O cartão da aula vive em `templates/partials/cartao_aula.html`,
  usado pelas duas vistas: são quatro estados com uma ordem que importa, e
  duplicá-los era garantir que um dia divergiam.
- `privacidade` (`/privacidade/`) — a política. **Sem login**, de propósito:
  tem de se poder ler antes de decidir criar conta. Os dados do responsável
  vêm das definições; enquanto faltarem, a página diz que falta preencher.

**Concorrência:** reservar/cancelar usam UPDATE condicional atómico e
`select_for_update`, à prova de duplo-clique / duas abas / última vaga.

---

## 7. Painel de administração (`bookings/admin.py`, `accounts/admin.py`)

Muito personalizado, para o Sérgio (não-técnico). Português em todo o lado.
Abas visíveis: **Utilizadores, Locais, Tipos de serviço, Sessões, Marcações,
Pacotes, Programa semanal**. Escondida: **Grupos** (`admin.site.unregister`).
(ClientPack e a app biblioteca foram apagados de todo.) Personalizações via CSS/
templates que estendem o admin — **sem pacotes de tema externos** (decisão:
não prender a manutenção a terceiros; o azul do Django fica como está).

**`static/css/admin-extra.css`** — correções de responsividade, carregado em
todas as páginas pelo `base_site.html`. Vai no bloco `responsive` e **depois**
do `block.super`, que é o último sítio onde o Django carrega folhas de estilo:
posto no `extrastyle` ficava antes da `responsive.css` dele e perdia todos os
empates de especificidade. Cobre: a barra de botões do topo (que flutuava por
cima do título), o painel de filtros a esmagar a tabela em tablet, o widget de
pesquisa a sair fora do ecrã, e os alvos de toque. Ao mexer no layout do
admin, **repetir a medição** — dois defeitos passaram por se ter auditado o
estado anterior e dado por bom para o novo.

**Overrides globais do admin** (`templates/admin/`):
- `base_site.html` — seta **"← Voltar"** (via `history.back()`, preserva
  pesquisa/filtros) no topo de fichas e confirmações de remoção.
- `search_form.html` — botão **"Limpar"** ao lado da contagem de resultados
  (limpa só a pesquisa). *(Cuidado JS: usar `new window.URL`, não `new URL`, em
  handlers inline.)*
- `checkbox_filter.html` — filtros de **multi-seleção** (o admin nativo só tem
  escolha única).

**Sessões (`SessionAdmin`)** — o ecrã mais trabalhado:
- Colunas: sessão, tipo, local, início, **"Inscritos"** (`3 / 12` clicável →
  Marcações filtradas por essa aula), **"Estado"** (Agendada verde / Concluída
  cinza / Cancelada vermelho — substitui o booleano `is_cancelled` invertido).
- Ordenação `-start` (mais recentes primeiro).
- **Tipo, local e lotação editáveis na própria lista** (`list_editable`), para
  o imprevisto de última hora (a aula de amanhã muda de local) sem abrir a
  ficha. A hora fica de fora: mudá-la é mudar a aula, e faz-se na ficha.
  O `autocomplete_fields` foi retirado — 3 tipos de serviço e 4 locais não
  justificam um widget de pesquisa que vai ao servidor e não encolhe com o
  ecrã (gravava uma largura fixa que saía fora da margem no telemóvel).
- Filtros **checkbox**: `EstadoFilter` (agendadas/concluídas/canceladas) e
  `TempoFilter` (futuras/passadas), combináveis entre si e com a barra de datas.
- **Cancelar é individual, não em massa** (após um cancelamento acidental por
  seleção múltipla): botão **"Cancelar esta aula"** (vermelho, à direita, com
  confirmação) na ficha da sessão; vira **"Reativar esta aula"** quando
  cancelada. Rotas próprias (`get_urls` → `cancelar_view`/`reativar_view`, só
  POST). O checkbox `is_cancelled` sai do formulário (`exclude`); o estado
  aparece em leitura. **Reativar NÃO reinscreve ninguém** (evita cobrar sem
  consentimento); avisa quantas marcações canceladas há para o Sérgio contactar.
  Ação em massa **"Reativar selecionadas"** existe (reativar não mexe créditos).
- **Widget de hora** no campo `start`: em vez de uma caixa "21:00", tem duas
  caixas **hora : minuto** (hora 0-23, minuto sugere 00/15/30/45, ambas com
  escrita livre; "9" → 09:00). Implementado com `HoraWidget` +
  `AdminSplitDateTimeHora` + templates em `bookings/templates/admin/widgets/`
  (`hora.html`, `split_datetime_hora.html`, que empilha data/hora com flex —
  o `<br>` do admin não quebra dentro da linha flex do campo). A data mantém
  o "Hoje" + calendário.

**Marcações (`BookingAdmin`)** — coluna **"Telemóvel"**: clicar pergunta
(confirm nativo) se quer abrir o WhatsApp com o aluno e abre `wa.me`; contas
sem número (ex.: admin) aparecem sem link. `lookup_allowed` autoriza o filtro
`session__id__exact` que vem da coluna "Inscritos".

**Programa semanal (`WeeklyProgramSlotAdmin`)** — botão **"Gerar aulas da
semana"** (`change_list.html` + `gerar_semana.html`), rota `gerar_semana_view`.

São **duas páginas com propósitos diferentes**, e isso é deliberado (chegou a
equacionar-se fundi-las; ver `PENDENTES.md`):
- A **lista** é o *molde*. O que se muda aqui vale para todas as semanas
  geradas daqui para a frente.
- A página de **gerar** são os ajustes *daquela semana*. Cada linha tem
  checkbox + dia + hora (fixa) + **tipo/local/lotação editáveis**,
  pré-preenchidos a partir do encaixe. O molde não é tocado.

A geração: escolhe a Segunda da semana (recua para Segunda se escolher outro
dia), cria só os encaixes ativos que ficaram marcados, e **nomeia cada aula**
nas mensagens em vez de dar contagens. Há uma opção **"atualizar as que já
existirem"** (desmarcada por defeito) que aplica os ajustes às aulas já
geradas **mantendo as inscrições** — recusa baixar a lotação abaixo dos
inscritos e recusa mudar o tipo de uma aula com gente (mudaria o balde de
créditos que a paga). **Nenhum caminho desta página apaga aulas**: apagar
levaria as marcações atrás em cascata e desinscrevia toda a gente sem aviso.
Para destruir uma aula existe o botão "Cancelar esta aula".

**Presenças (`presencas_view`)** — botão **"Marcar presenças"** na ficha da
aula, com um rádio por aluno (Por marcar / Veio / Faltou). Rádios e não uma
lista pendente: o Sérgio usa isto com o telemóvel na mão no fim da aula, e
uma lista obrigava a abrir-ler-escolher por pessoa. **Não mexe em créditos
nenhuns** e não escreve no livro de movimentos — faltar não devolve o
crédito (é o que faz cancelar a tempo) e vir já foi cobrado na reserva. Quem
cancelou não aparece: cancelou a tempo, recebeu o crédito, não é uma falta.

**Histórico do aluno (`historico_view`, em `accounts/admin.py`)** — saldos,
extrato de créditos e aulas, numa página só, ligada da coluna "Histórico" da
lista de Utilizadores. Existe para a pergunta que o Sérgio mais vai receber:
"comprei 10, fui a 3, porque é que tenho 5?". Respeita a regra das contas de
admin — o Sérgio não vê o histórico de um administrador.

**Aulas de amanhã (`lembretes_view`)** — botão no topo da lista de Sessões.
Mostra quem tem aula no dia seguinte, com o número a abrir o WhatsApp. Só
amanhã: hoje já não dá jeito avisar, e depois de amanhã ainda vai a tempo.
Aulas sem inscritos não aparecem — não há lá quem avisar. Mesmo princípio da
lista de espera: a app junta a informação, o aviso é do Sérgio.

**Lista de espera (`ListaEsperaAdmin`)** — o ecrã **"quem falta avisar"**.
Quando alguém sobe da fila fica inscrito sem saber: a app não manda
mensagens, por isso esta lista é o aviso ao Sérgio. Abre já filtrada por
quem falta avisar (`PorAvisarFilter`, que deita fora o "Todos" do Django —
aqui ele daria a mesma lista e faria duvidar do que se está a ver); clicar no
número abre o WhatsApp; a ação **"Marcar como avisado"** tira a linha dali.
Não se acrescentam entradas por aqui (entra-se na fila pelo site) e o aluno,
a aula e as datas são só de leitura — são o registo do que aconteceu.

**Utilizadores (`accounts/admin.py`)** — 3 saldos editáveis na lista
(`list_editable`), filtro "Faz anos hoje" (`BirthdayTodayFilter`), **sem remoção
em massa** (`get_actions` remove `delete_selected`), sem campos de grupos/
permissões na ficha (só um superuser).

---

## 8. Segurança

- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` vêm de **variáveis de ambiente** (com
  defaults só de dev). `db.sqlite3` e `.claude/` no `.gitignore`.
- **Throttle de login** (`accounts.views.ThrottledLoginView`): após 5 falhas
  seguidas (mesmo IP + número, contagem na cache) bloqueia 15 min. Importante
  porque as passwords têm mínimo de só 6 caracteres. **Nota deploy:** atrás de
  proxy, `REMOTE_ADDR` passa a ser o IP do proxy — rever para usar o cabeçalho
  correto.
- Passwords: só `MinimumLengthValidator` (6), por opção (público pouco técnico,
  sem dados sensíveis nem pagamentos na app).
- **Revisão de segurança (jul 2026):** CSRF ok (todos os POST com token), sem SQL
  raw (só ORM), autorização ok (`cancel_booking`/`my_bookings` scoped ao user,
  views de admin verificam permissões). Corrigida **1 XSS armazenada**: o nome do
  aluno ia num `onclick` da coluna Telemóvel e podia injetar JS no painel do
  Sérgio — agora vai em `data-nome` e é lido com `this.dataset.nome`.
- **Travão também no `/admin/login/`** (set 2026). A rota está declarada em
  `config/urls.py` **antes** do `admin.site.urls` para ganhar o pedido, e usa
  `com_travao()` (em `accounts/views.py`), que envolve a view de login do
  admin em vez de a reescrever — ela tem template e contexto próprios. A
  contagem usa a **mesma chave** do login do site, de propósito: as duas
  portas dão à mesma conta e alternar entre elas não pode render o dobro das
  tentativas. Vai passar a haver mais do que um administrador (ver secção 11).
- **A cache do travão vive na base de dados**, não na memória do processo
  (`CACHES` → `DatabaseCache`, tabela `cache_do_travao`). Com a cache de
  memória, cada worker do gunicorn contava as suas tentativas — cinco
  workers davam cinco vezes mais tentativas antes de bloquear — e um
  redeploy limpava tudo: o travão parecia existir e quase não travava.
  Escolheu-se a tabela em vez de Redis por ser a mesma base de dados que já
  existe, sem serviço nem custo novos. A tabela é criada por **migração**
  (`accounts/0005_cache_do_travao.py`), para não depender de ninguém se
  lembrar de um comando no deploy.
- **RGPD** (set 2026): política em `/privacidade/` (aberta a quem não tem
  conta — tem de se poder ler antes de aceitar), consentimento obrigatório no
  registo com a data guardada em `User.consentimento_em` (a prova; só de
  leitura no admin), e o apagamento de um utilizador leva marcações e
  movimentos em cascata. Os dados do responsável vêm de `RGPD_RESPONSAVEL`,
  `RGPD_CONTACTO` e `RGPD_PRAZO_ANOS`, **obrigatórias em produção** — a app
  recusa arrancar sem elas, como já fazia com o `SERGIO_WHATSAPP`.
- O `settings.py` **já está preparado para produção**: bloco `if not DEBUG` com
  `SECURE_SSL_REDIRECT`, cookies seguros, HSTS, `SECURE_PROXY_SSL_HEADER`;
  WhiteNoise; PostgreSQL via `DATABASE_URL`; `CSRF_TRUSTED_ORIGINS`. O
  `check --deploy` só acusa avisos **localmente** (DEBUG=True); em produção
  resolvem-se — exceto a `SECRET_KEY`, que tem de ser posta por env var. Ver
  `DEPLOY.md` para os passos do Railway.

---

## 9. Marca / visual (site)

- Tema escuro. Paleta em `static/img/brand/MARCA.md`: preto `#0F0F0F`, cinza
  `#202020`, verde vivo `#5DD62C`, verde escuro `#337418`, branco `#F8F8F8`.
  Variáveis no `:root` de `static/css/style.css`.
- **Fonte de destaque: Oswald** (Google Fonts) em títulos, cartões e botões
  (maiúsculas, estilo cartaz); corpo na fonte de sistema.
- **Cores por tipo de crédito** (categóricas, não semáforo): SG verde `#5DD62C`,
  PT teal `#2CC5D6`, Hybrid violeta `#9B7CF0`. Aparecem na **faixa de saldos**
  (3 contadores centrados no topo, só para alunos — `not user.is_staff`) e nos
  **selos** dos cartões de aula e de pacote.
- Imagens em `static/img/brand/`: `logo-restart-now.png`, `class-outdoor.jpg`,
  `class-indoor.jpg`, `class-online.jpg` (todas otimizadas a ~1600px). O cartão
  de aula escolhe a imagem pelo local (indoor/outdoor/online).
- **`favicon.png`** — a seta circular verde do logótipo, isolada e posta num
  quadrado preto. É a marca, não o texto: o wordmark a 16px seria ilegível.
- **Etiquetas de partilha** (`templates/partials/meta.html`) — Open Graph,
  `description`, `theme-color` e favicon, partilhados pelos dois templates
  base. Existem por causa do WhatsApp, que é o canal deste negócio: sem elas o
  link colado aparece como texto sem imagem nem título. O `og:image` é
  construído a partir do pedido, por isso funciona em dev, no túnel e em
  produção sem ninguém trocar nada.
- `base.html` — barra de topo com **menu hambúrguer** abaixo de 720px; foco
  visível (`:focus-visible` verde); link "Saltar para o conteúdo" e a lista de
  avisos com `aria-live` (usada também pelo JS do horário, para o aviso de
  reserva ser indistinguível de uma mensagem do servidor — não há `alert()`).
  Login/registo usam `base_auth.html`.
- **Alvos de toque de 44px** em ecrãs estreitos (Apple HIG). No admin ficaram
  mais contidos (34-40px): é uma ferramenta densa e 44px desproporcionava-a.
  Medir com `min-height`, não com padding — o padding depende do tamanho da
  letra e da entrelinha, e a primeira tentativa no link do rodapé deu 43px.
- **O service worker NÃO é registado em DEBUG** (set 2026). Em produção o
  WhiteNoise dá nomes com hash aos estáticos, por isso um ficheiro alterado
  tem endereço novo e a cache do worker nunca serve o antigo. Em
  desenvolvimento não há hash: o worker guardava o CSS e continuava a
  servi-lo depois de o ficheiro mudar — mexia-se no CSS, recarregava-se, e
  a página ficava igual. A única pista era a folha servida ter menos bytes
  do que o ficheiro em disco. Ver `bookings/context_processors.py`.
- **Tabelas escritas à mão no admin** (histórico, presenças) vão dentro de
  `.tabela-rolavel` (`admin-extra.css`): rolam na própria caixa em vez de
  arrastarem a página. As listas do admin já fazem isto sozinhas; as nossas
  não faziam, e o histórico transbordava 219px a 360px de largura.
- **Comentários de template:** `{# #}` só numa linha — comentário multi-linha
  vira texto na página. Usar sempre `{% comment %}...{% endcomment %}`.
  (Este erro já ocorreu 2×; verificar sempre no browser após mexer em templates.)

---

## 10. Testes

**153 testes** (`accounts/tests.py`, `bookings/tests.py`), todos a passar:
throttle de login, normalização/registo/login por telemóvel, isolamento de
créditos por tipo, reembolsos (cancelar sessão, apagar sessão/marcação, cancelar
reserva), filtros e ações do admin de Sessões, coluna Telemóvel, gerador do
programa semanal (inc. não-duplicar, ajustes aplicados à aula e não ao molde,
atualizar sem perder inscrições, e as recusas de lotação e de tipo), limites de
navegação do horário, imagem do cartão, o widget de hora, aulas passadas sem
botão de reservar, etiquetas de partilha, preços escondidos e autofill do
registo, o travão do login do admin, o consentimento de privacidade e o
apagamento de dados, e o número de consultas por ecrã. Correr sempre
`manage.py test accounts bookings` antes de commitar mudanças de lógica.

**Testes de consultas (`ConsultasPorEcraTests`)** — comparam o mesmo ecrã com
poucas e com muitas aulas e exigem o **mesmo** número de consultas. Comparar
em vez de fixar um número evita um teste que parte sempre que se acrescenta
uma consulta inofensiva; o que ele protege é o N+1 não voltar.

---

## 11. Estado atual

**FEITO:** estrutura e modelos; login/registo por telemóvel com normalização;
créditos por tipo (SG/PT/Hybrid) com reserva/cancelamento/reembolso atómicos
e livro de movimentos que explica cada saldo;
horário por dia com limites e os quatro estados do cartão; programa semanal +
gerador com ajustes por semana; pacotes com WhatsApp (sem preços); admin muito
personalizado (cancelar/reativar por aula, filtros checkbox, coluna Inscritos e
Telemóvel, widget de hora, seta Voltar, botão Limpar, edição em linha nas
Sessões); tema visual RESTART NOW com faixa de saldos e selos por tipo;
etiquetas de partilha e favicon; responsividade verificada em todo o site e
admin (360/390/768/1024/1400px); throttle de login nas duas portas (site e
`/admin/`), com a contagem na base de dados; recuperação via WhatsApp; base
de RGPD (política, consentimento, apagamento); lista de espera com o ecrã de
avisos; presenças, histórico do aluno e aulas de amanhã; vista de semana;
instalar no telemóvel (PWA); linter e integração contínua;
**153 testes**; GitHub ligado (privado).

**POR FAZER (ver `PENDENTES.md` para o detalhe):**
1. **Info do Sérgio sobre pacotes** — nomes/nº de sessões/`credit_type` reais;
   confirmar a natureza do "Hybrid"; `credit_type` de cada Tipo de Serviço
   (ficaram Small Group por defeito). Os dados atuais são de teste. Confirmar
   também as quatro decisões construídas com o padrão do setor (lista de
   espera, faltas, expiração — ver `PENDENTES.md`).
2. **Corrigir dois encaixes do programa semanal** — Segunda 07:00 e 08:00 estão
   como "PT Individual" com lotação 12. É um resto dos testes: geradas assim,
   criam aulas individuais com doze vagas a cobrar créditos de PT.
3. **Deploy no Railway** — o **código já está preparado** (gunicorn,
   whitenoise, PostgreSQL via `DATABASE_URL`, segurança HTTPS atrás de proxy,
   throttle com IP real, `Procfile` com `collectstatic`, `.python-version`,
   `.env.example`). Ensaiado com `DEBUG=False` num túnel: `check --deploy`
   passa limpo. Falta a parte manual: criar a conta no Railway, ligar o
   repositório, adicionar o PostgreSQL e definir as variáveis. **Passo a passo
   em `DEPLOY.md`.** Alojamento ~5–12€/mês (cliente).
4. **`SERGIO_WHATSAPP`** — em produção define-se por variável de ambiente (o
   default no código é o número de TESTE do André).
5. **Limpar dados de teste** antes do deploy: User1/2/3, Ana Teste, Ananas, o
   superuser **`claude-preview`**, os 12 alunos com `(demo)` no apelido, a
   conta `912000000`, e as aulas com `DEMO - apagar antes do deploy` no campo
   de notas.
6. **Dar acesso de administrador a mais alguém** — as regras já existem
   (quem não é superuser não mexe em contas de admin), mas atribui-se pelo
   painel de permissões do Django, que é denso e em inglês. Se um dia for
   preciso com frequência, vale um ecrã próprio.

*(Ficaram feitos em set 2026: o **rasto dos créditos** — `MovimentoCredito`,
secção 5; as **cópias de segurança** — `scripts/backup.ps1`; as **páginas de
erro** e o **registo de erros** — `templates/404.html`, `500.html`, `LOGGING`;
o **travão no login do admin** e o **N+1 das contagens** — ver abaixo; e a
**base do RGPD** — política, consentimento e apagamento.)*

**Decisões fechadas (não fazer):** sem lembrete automático de aniversários (só
o filtro manual "Faz anos hoje"); sem pagamentos online; sem integração de
WhatsApp na app (a app Business grátis é uma opção só para uso do Sérgio, à
parte); `ClientPack` apagado de todo.

---

## 12. Notas / cuidados (resumo)

- UI, mensagens e admin **sempre em pt-PT**. Manter tudo **simples**.
- Ao mexer no CSS: **Ctrl+F5** (cache do browser).
- Templates de **widgets** de formulário vivem em `<app>/templates/`, não na
  pasta de projeto (o renderizador de formulários procura nas apps).
- Comentários de template multi-linha: `{% comment %}`, nunca `{# #}`.
- Commits no PowerShell 5.1: **sem aspas duplas** na mensagem. O PowerShell 5.1
  também **não aceita `&&`** para encadear comandos — usar `;`.
- `db.sqlite3` é local (gitignored) — mudar dados no admin/shell **não** vai
  para o Git; só o código vai. É por isso que a base de dados de
  desenvolvimento tem de ser copiada à mão quando o projeto muda de máquina.
- **Ao mexer no layout, voltar a medir.** Auditar antes de alterar e dar o
  resultado por bom para depois já custou dois defeitos: uma tabela que passou
  a arrastar a página inteira (e a cortar o cabeçalho) por lhe terem sido
  acrescentadas colunas, e dois botões com alturas diferentes por um ser
  `<input>` (border-box) e o outro `<a>` (content-box).
