# RESTART NOW — marcação de aulas (Django)

Plataforma para um personal trainer (cliente: **Sérgio**). Os alunos registam-se
com o telemóvel, veem o horário e **reservam aulas gastando créditos**. Os
créditos compram-se em pacotes negociados pelo WhatsApp — o pagamento é tratado
pelo treinador, fora da app.

**Django 5.1** + templates server-rendered + JS mínimo. SQLite em
desenvolvimento, PostgreSQL em produção. Tudo em português de Portugal.

> **Contexto completo do projeto em [`CLAUDE.md`](CLAUDE.md)** — decisões de
> negócio, modelos, admin, segurança e estado atual. É por aí que se começa,
> tanto para uma pessoa como para um assistente de IA.

---

## Pôr a correr numa máquina nova

Precisas de **Python 3.12** (é o que o `.python-version` declara e o que a
produção usa; o Django 5.1 vai só até ao 3.13).

```powershell
git clone https://github.com/nghxst14/Fitness-Classes-Management-App.git
cd Fitness-Classes-Management-App
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Depois abre **http://127.0.0.1:8000/** (site) ou **/admin/** (painel).

**Notas:**

- `py -3.12` e não `python`: pode haver mais do que uma versão instalada, e o
  `python` solto aponta para a mais recente. Confirma com
  `.\venv\Scripts\python.exe --version`.
- Não corras `makemigrations` — as migrações já estão no repositório. Só o
  `migrate` é preciso.

Comandos do dia-a-dia em [`GUIA_COMANDOS.md`](GUIA_COMANDOS.md).

---

## ⚠️ O que NÃO vem no repositório

Isto é o que costuma apanhar quem muda de máquina. O Git traz o **código**, não
os **dados**:

| O quê | Como obter |
|---|---|
| **`db.sqlite3`** — a base de dados de desenvolvimento | **Copiar à mão** da outra máquina (fica na raiz do projeto, ao lado do `manage.py`). Sem ela ficas com uma app vazia: sem locais, sem tipos de aula e sem os 23 encaixes do programa semanal. |
| `venv/` | Recriar com os comandos acima. Não é portátil — aponta para o caminho absoluto do Python que o criou. |
| `staticfiles/` | Gerado pelo `collectstatic`; só é preciso em produção. |
| `.env` | Só existe em produção (ver [`.env.example`](.env.example)). |

Alternativa a copiar o ficheiro: [`scripts/backup.ps1`](scripts/backup.ps1) faz
uma exportação em JSON que se restaura com `loaddata` — ver
[`GUIA_COMANDOS.md`](GUIA_COMANDOS.md), secção 10.

---

## Como está organizado

```
accounts/    utilizador (login por telemóvel) e os 3 saldos de créditos
bookings/    o núcleo: aulas, marcações, créditos, programa semanal, admin
config/      settings, urls
templates/   HTML do site + personalizações do admin
static/      CSS e imagens da marca
scripts/     backup.ps1 (cópias) e demonstracao.ps1 (mostrar a alguém de fora)
```

### Os modelos

```
User (accounts)
 ├─ login pelo telemóvel (guardado no campo username)
 └─ 3 saldos: sessoes_sg / sessoes_pt / sessoes_hybrid

Location ─┐
ServiceType ─┼─> Session ──< Booking >── User
             │      (uma aula          (inscrição)
             │       concreta)
WeeklyProgramSlot ──> gera Sessions de uma semana de uma vez

Pack                 produto de créditos (venda pelo WhatsApp)
MovimentoCredito     o extrato: uma linha por cada alteração de saldo
```

**Créditos por tipo:** há três categorias (Small Group, PT, Hybrid) e cada
aluno tem um saldo de cada. Uma aula declara qual gasta — um crédito de Small
Group **não** paga uma aula de PT.

---

## Os outros documentos

| Ficheiro | Para quê |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | O contexto todo: decisões, modelos, admin, segurança. **Ler primeiro.** |
| [`GUIA_COMANDOS.md`](GUIA_COMANDOS.md) | Comandos passo a passo, cópias de segurança, problemas comuns |
| [`PENDENTES.md`](PENDENTES.md) | Decisões à espera do cliente e o que já ficou fechado |
| [`DEPLOY.md`](DEPLOY.md) | Pôr online no Railway |
| [`static/img/brand/MARCA.md`](static/img/brand/MARCA.md) | Paleta e logótipo |
| [`docs/referencias-ui.md`](docs/referencias-ui.md) | Inspiração visual |

---

## Estado

Funciona ponta a ponta: registo e login por telemóvel, horário, reservas e
cancelamentos com os créditos tratados de forma atómica, programa semanal com
gerador, pacotes ligados ao WhatsApp, e um painel de administração muito
personalizado para uma pessoa não técnica.

**87 testes**, todos a passar:

```powershell
python manage.py test accounts bookings
```

Ainda **não está no ar**. O que falta para lá chegar — e o que falta depois —
está em [`CLAUDE.md`](CLAUDE.md), secção 11, e em
[`PENDENTES.md`](PENDENTES.md).
