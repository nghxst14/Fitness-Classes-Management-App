# Deploy — pôr a app online no Railway

> O **código** já está preparado (ver commit "Prepara o codigo para deploy no
> Railway"). Este guia é a **tua** parte: criar a conta, ligar o GitHub, a base
> de dados e as variáveis. Não há mais código a escrever para publicar.
>
> O que o Railway faz sozinho a cada `git push`: instala o `requirements.txt`,
> corre `collectstatic`, corre as migrações (`release` no `Procfile`) e arranca
> a app com o gunicorn.

---

## 0. Antes de começar — gera a SECRET_KEY

No terminal do projeto (com a venv ativa), corre:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copia o resultado (uma linha comprida de símbolos). Vais colá-lo numa variável
no Railway (passo 4). **Não** o metas no código nem no Git.

---

## 1. Cria a conta no Railway

1. Vai a **railway.app** → *Login* → entra com o **GitHub** (a conta `nghxst14`).
2. Confirma o email se for pedido. O plano inicial precisa de um cartão
   associado (custo ~5–10€/mês conforme o uso); confirma isto com o Sérgio,
   porque o alojamento é a cargo do cliente.

## 2. Cria o projeto a partir do repositório

1. *New Project* → **Deploy from GitHub repo**.
2. Autoriza o Railway a aceder ao GitHub e escolhe
   **Fitness-Classes-Management-App**.
3. O Railway começa logo um primeiro deploy — **vai falhar ou ficar sem base
   de dados**; é normal, faltam a base de dados e as variáveis (passos 3 e 4).

## 3. Adiciona o PostgreSQL

1. Dentro do projeto: *New* → *Database* → **Add PostgreSQL**.
2. Não é preciso configurar nada: o Railway cria a variável **`DATABASE_URL`**
   e liga-a automaticamente à app. O nosso `settings.py` já a lê.

## 4. Define as variáveis de ambiente

No serviço da **app** (não no da base de dados): separador **Variables** →
adiciona estas (ver também `.env.example`):

| Variável | Valor |
|---|---|
| `DJANGO_SECRET_KEY` | a chave gerada no passo 0 |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | o domínio que o Railway te der (ex.: `nome.up.railway.app`) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | o mesmo domínio com `https://` à frente |
| `SERGIO_WHATSAPP` | `351913621166` (o número real do Sérgio) |
| `RGPD_RESPONSAVEL` | `Sérgio Luís Marques e Silva Paulo` |
| `RGPD_CONTACTO` | `351913621166` (o WhatsApp dele serve; não tem de ser email) |
| `RGPD_PRAZO_ANOS` | `2` (decidido pelo André, set 2026) |

> O domínio: em *Settings → Networking → Generate Domain*. Depois de o gerar,
> volta às Variables e mete-o nas duas variáveis de host acima. **Guarda e
> deixa fazer o redeploy.**

> **As três `RGPD_*` já estão todas.** A app recusa arrancar sem elas, de
> propósito: uma política publicada sem responsável não é uma política, e
> quem responde legalmente pelos dados dos alunos é o Sérgio, não quem fez a
> app. O nome vai aparecer na página `/privacidade/`, que é público — é
> mesmo esse o objetivo: o aluno tem de saber a quem se dirigir.

## 5. Cria o teu utilizador de administração

Depois de a app estar online e as migrações corridas (passo automático), abre
uma consola no serviço da app: *(no separador do serviço)* **⋮ → Shell**, ou
usa o comando do Railway CLI, e corre:

```
python manage.py createsuperuser
```

Segue as perguntas (username = um telemóvel ou "admin", e uma password). É com
esta conta que o Sérgio entra em `/<dominio>/admin/`.

## 6. Verifica

- Abre `https://<dominio>/` — deve mostrar o site.
- Abre `https://<dominio>/admin/` — entra com o superuser.
- Testa: cria um Tipo de Serviço, uma Sessão, e regista um aluno pelo site.

---

## Cópias de segurança — antes de haver créditos pagos

**Fazer isto antes de o Sérgio começar a somar créditos a sério.** A partir
desse momento, a base de dados deixa de ser "dados da app" e passa a ser
dinheiro que os alunos já pagaram — e que não se consegue reconstruir, porque
o pagamento aconteceu numa conversa de WhatsApp.

São duas camadas, e as duas fazem falta:

- [ ] **Ligar as cópias automáticas do PostgreSQL no Railway.** Protege-te do
      erro comum: uma migração infeliz, um apagar a mais no admin, uma ação em
      massa que levou coisas atrás em cascata.
- [ ] **Guardar uma cópia FORA do Railway.** É a camada que as pessoas saltam e
      a que conta no dia em que conta: as cópias do Railway vivem dentro da
      conta do Railway e vão atrás se a conta for suspensa, se o pagamento
      falhar ou se alguém apagar o serviço. Faz-se com
      `.\scripts\backup.ps1 -Producao` (ver `GUIA_COMANDOS.md`, secção 10).
- [ ] **Testar um restauro. Uma vez, a sério.** Uma cópia por testar não é uma
      cópia: uma cópia estragada parece perfeitamente normal e só se revela
      imprestável no dia em que precisas dela. As duas primeiras cópias que
      este projeto produziu **não restauravam** — e ambas pareciam bem. O
      procedimento está no `GUIA_COMANDOS.md`, secção 10.

## Depois do deploy (checklist final)

- [ ] **Limpar dados de teste** (se algum foi para a base de dados de produção):
      User1/2/3, Ana Teste, aulas e pacotes fictícios. **Fazer uma cópia
      primeiro** — apagar em massa é precisamente quando isto salva.
- [ ] **Configurar os pacotes e os tipos de serviço reais** com o Sérgio
      (nomes, nº de sessões, preços, `credit_type`).
- [ ] **Rever o Programa semanal** (tipo/local de cada encaixe).
- [ ] **Lembrete de aniversários**: se um dia se quiser, é uma tarefa agendada
      (Railway *Cron*) a correr um comando de gestão — fica para depois.
- [ ] **Formação do Sérgio** (mini-guia do admin).

## Segurança — o que já ficou resolvido

O código está preparado (HTTPS, HSTS, cookies seguros — bloco `if not DEBUG`).
Os pontos que a revisão de jul 2026 deixou em aberto **foram todos fechados**
em set 2026:

- [x] **Throttle atrás de proxy.** Lê o IP real do `X-Forwarded-For` (o
      `REMOTE_ADDR` no Railway é o do proxy, e seria o mesmo para toda a
      gente — um ataque a uma conta bloquearia os logins de todos).
- [x] **Login do admin com travão.** O `/admin/login/` passou a ter o mesmo
      limite de tentativas do login do site, com a **mesma** contagem: as duas
      portas dão à mesma conta e alternar entre elas não pode render o dobro
      das tentativas.
- [x] **A contagem vive na base de dados**, não na memória do processo. Com
      vários workers do gunicorn, cada um contava as suas tentativas e um
      redeploy limpava tudo — o travão parecia existir e quase não travava.
- [x] **XSS armazenada na coluna Telemóvel** — o nome do aluno passou a ir em
      `data-nome` em vez de dentro do `onclick`.

Continua a valer o óbvio: **password forte** na conta de administração, e de
preferência sem o username "admin".

## Notas

- **Custo:** ~5–12€/mês (app + PostgreSQL), a cargo do cliente. A manutenção do
  André é separada.
- **Atualizações:** a partir daqui, cada `git push` para o `master` faz um novo
  deploy automático. As migrações correm sozinhas (`release` no `Procfile`).
- **Domínio próprio** (ex.: `restartnow.pt`): opcional, liga-se em
  *Settings → Networking → Custom Domain* e acrescenta-se às duas variáveis de
  host. Fica para quando o cliente quiser.
