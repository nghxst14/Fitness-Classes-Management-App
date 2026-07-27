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
| `SERGIO_WHATSAPP` | o número real do Sérgio (ex.: `351XXXXXXXXX`) |

> O domínio: em *Settings → Networking → Generate Domain*. Depois de o gerar,
> volta às Variables e mete-o nas duas variáveis de host acima. **Guarda e
> deixa fazer o redeploy.**

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

## Depois do deploy (checklist final)

- [ ] **Limpar dados de teste** (se algum foi para a base de dados de produção):
      User1/2/3, Ana Teste, aulas e pacotes fictícios.
- [ ] **Configurar os pacotes e os tipos de serviço reais** com o Sérgio
      (nomes, nº de sessões, preços, `credit_type`).
- [ ] **Rever o Programa semanal** (tipo/local de cada encaixe).
- [ ] **Lembrete de aniversários**: se um dia se quiser, é uma tarefa agendada
      (Railway *Cron*) a correr um comando de gestão — fica para depois.
- [ ] **Formação do Sérgio** (mini-guia do admin).

## Notas

- **Custo:** ~5–12€/mês (app + PostgreSQL), a cargo do cliente. A manutenção do
  André é separada.
- **Atualizações:** a partir daqui, cada `git push` para o `master` faz um novo
  deploy automático. As migrações correm sozinhas (`release` no `Procfile`).
- **Domínio próprio** (ex.: `restartnow.pt`): opcional, liga-se em
  *Settings → Networking → Custom Domain* e acrescenta-se às duas variáveis de
  host. Fica para quando o cliente quiser.
