# Guia de comandos — RESTART NOW

Referência dos comandos que vais usar neste projeto, com uma descrição do que
cada um faz. Corre-os no **PowerShell**, dentro da pasta do projeto
(`Fitness-Classes-Management-App`), com o ambiente virtual ativo (ver secção 1).

> **Nota do PowerShell 5.1:** não aceita `&&` para encadear comandos — usa `;`.
> E nas mensagens de commit, evita aspas duplas: partem o parser.

---

## ⚡ Arranque rápido (reabrir o projeto)

Sempre que voltas ao projeto depois de o teres fechado, são só estes passos:

```powershell
venv\Scripts\activate
python manage.py runserver
```

Depois abre no browser `http://127.0.0.1:8000/` (site) ou
`http://127.0.0.1:8000/admin/` (painel de gestão).
Para **parar** o servidor: `Ctrl + C`.

> Não é preciso `pip install` nem migrações no dia-a-dia — só quando a `venv` é
> nova ou quando algo muda (ver secções seguintes). Para parar o servidor e
> continuar a usar o terminal, `Ctrl + C`.

---

## 1. Ambiente virtual (venv)

O ambiente virtual é uma "caixa" isolada onde ficam as bibliotecas deste projeto
(como o Django), sem se misturarem com o resto do computador.

```powershell
py -3.12 -m venv venv
```
Cria o ambiente virtual (só é preciso **uma vez**, ou quando for preciso
recriá-lo).

> **Porquê `py -3.12` e não `python`?** Porque há mais do que uma versão do
> Python instalada nesta máquina (o 3.12 para este projeto, o 3.14 para o
> resto), e o `python` solto aponta para a **mais recente**. Se criares o venv
> com `python`, ficas silenciosamente com um venv 3.14 — que não é a versão
> que o `.python-version` declara nem a que o Railway usa, e que o Django 5.1
> nem sequer suporta oficialmente (vai só até ao 3.13).
>
> Isto **já partiu este projeto uma vez**: o venv tinha ficado num 3.13 que
> depois desapareceu, e a app deixou de arrancar. Ver as versões disponíveis:
> `py --list`.

```powershell
venv\Scripts\activate
```
Ativa o ambiente. Tens de fazer isto **sempre que abres um terminal novo** para
trabalhar. Quando está ativo, aparece `(venv)` no início da linha — e a partir
daí `python` significa o 3.12 do projeto, não o 3.14 do sistema.

```powershell
.\venv\Scripts\python.exe --version
```
Confirma que o venv está na versão certa. Deve dizer **Python 3.12.x**. Se
disser outra coisa, o venv foi criado com a versão errada: apaga a pasta
`venv` e volta ao primeiro comando desta secção.

```powershell
deactivate
```
Sai do ambiente virtual (raramente necessário; basta fechar o terminal).

---

## 2. Dependências (bibliotecas)

```powershell
pip install -r requirements.txt
```
Instala todas as bibliotecas de que o projeto precisa, listadas no ficheiro
`requirements.txt`. Corre isto depois de criar o venv, ou sempre que forem
adicionadas novas dependências.

```powershell
pip freeze
```
Mostra as bibliotecas instaladas e as suas versões (útil para confirmar).

---

## 3. Base de dados e migrações

> Explicação completa do que são as migrações mais abaixo, na secção "O que são
> as migrações?".

```powershell
python manage.py makemigrations
```
Lê os modelos (os ficheiros `models.py`) e **cria as instruções** de alteração
da base de dados quando algo mudou (um campo novo, um modelo novo, etc.).
Gera ficheiros na pasta `migrations` de cada app.

```powershell
python manage.py migrate
```
**Aplica** essas instruções à base de dados, criando/alterando as tabelas.
Corre sempre este a seguir ao `makemigrations`. Na primeira vez, cria toda a
base de dados.

```powershell
python manage.py showmigrations
```
Lista as migrações e mostra quais já foram aplicadas (com um `[X]`).

---

## 4. Contas de administração

```powershell
python manage.py createsuperuser
```
Cria uma conta com acesso total ao painel de administração (`/admin/`).
Pede username, email e password. Podes correr várias vezes para criar mais.

---

## 5. Arrancar o servidor

```powershell
python manage.py runserver
```
Arranca o servidor de desenvolvimento. Depois abre no browser
`http://127.0.0.1:8000/`. Para **parar** o servidor: `Ctrl + C` no terminal.
O servidor recarrega sozinho quando gravas alterações no código.

Este é o servidor para **trabalhares**. Só funciona no teu computador — mais
ninguém lhe consegue chegar, e é isso que o torna rápido e seguro.

---

## 5b. Mostrar o site a alguém de fora (ao Sérgio, por exemplo)

Quando o Sérgio precisar de abrir o site no telemóvel dele, de qualquer rede,
há um script que trata de tudo:

```powershell
.\scripts\demonstracao.ps1
```

O que ele faz, por esta ordem: prepara os ficheiros estáticos, arranca o
servidor com as definições de **produção** (as mesmas do Railway), abre um
túnel público e **só te dá o endereço depois de confirmar que responde**.
Carregas Enter e fecha tudo — servidor e túnel.

Da primeira vez é preciso instalar a ferramenta do túnel:

```powershell
winget install --id Cloudflare.cloudflared --source winget
```

**Coisas a saber:**

- O endereço é **sorteado a cada arranque**. Não dá para manter o mesmo link:
  se fechares e voltares a abrir, tens de mandar o novo.
- Morre quando o computador suspender ou quando fechares o script. Serve para
  uma sessão combinada contigo por perto, **não** para o Sérgio ir
  experimentando ao longo da semana. Para isso é preciso o alojamento a sério
  (ver `DEPLOY.md`).
- Enquanto está aberto, **o `/admin/` fica acessível a quem tenha o endereço**.
  O endereço é impossível de adivinhar, mas confirma que a password do admin é
  longa antes de espalhares o link.
- Corre com `DEBUG=False` de propósito: é o mesmo ambiente do Railway, por isso
  serve de ensaio geral do deploy.

---

## 6. Abrir o terminal na pasta certa

- No Explorador de Ficheiros, abre a pasta do projeto, clica na **barra de
  endereço**, escreve `powershell` e Enter. Abre já no sítio certo. É a forma
  mais fiável, porque não depende de decorares o caminho.
- Ou, num terminal qualquer, `cd` para a pasta onde clonaste o repositório.
  Se o caminho tiver espaços ou acentos, mete-o entre aspas.

> O caminho **não é o mesmo em todas as máquinas** — depende de onde clonaste.
> Por isso este guia não o fixa em lado nenhum.

---

## 7. Git (controlo de versões)

O Git guarda o histórico do projeto. Cada "commit" é um ponto de salvaguarda a
que podes sempre voltar.

```powershell
git status
```
Mostra o que mudou desde o último commit (ficheiros alterados, novos, etc.).

```powershell
git add -A
```
Marca **todas** as alterações para entrarem no próximo commit ("preparar").

```powershell
git commit -m "descrição curta do que mudou"
```
Guarda as alterações preparadas no histórico, com uma mensagem que descreve o
que foi feito. Ex.: `git commit -m "Adiciona pagina de contactos"`.

```powershell
git log --oneline
```
Mostra a lista de commits (o histórico), um por linha.

```powershell
git diff
```
Mostra exatamente as linhas que mudaram desde o último commit.

```powershell
git restore NOME_DO_FICHEIRO
```
Desfaz as alterações **não guardadas** de um ficheiro (volta ao último commit).
Cuidado: perde o que não foi commitado.

**Fluxo típico depois de mexer no código:** `git status` → `git add -A` →
`git commit -m "..."`.

---

## 8. Passwords dos alunos

**Não há recuperação por email.** Foi decisão do projeto: o Sérgio vive no
WhatsApp e o email não é usado em lado nenhum (os alunos entram com o número de
telemóvel, não com email).

O link **"Esqueci-me da password"** na página de login abre a conversa de
WhatsApp com o Sérgio, com a mensagem já escrita. Ele redefine a password no
admin: *Utilizadores → o aluno → no campo da password, o link "alterar"*.

> Isto explica também porque é que o aluno **não pode mudar a password
> sozinho** — não existe essa página. Está anotado como lacuna em
> `CLAUDE.md`, secção 11.

---

## 9. Problemas comuns

- **`python` não é reconhecido** → o Python não está instalado ou não está no
  PATH. Reinstala a partir de python.org e marca "Add Python to PATH".
- **Não aparece `(venv)`** → esqueceste-te de correr `venv\Scripts\activate`.
- **A página dá erro depois de mexer nos modelos** → provavelmente falta correr
  `makemigrations` + `migrate`.
- **O `runserver` diz "That port is already in use"** → já tens um servidor a
  correr noutro terminal, ou usa outra porta: `python manage.py runserver 8001`.
- **Erros estranhos a importar bibliotecas, ou o Django a queixar-se da versão
  do Python** → o venv pode ter sido criado com a versão errada. Confirma com
  `.\venv\Scripts\python.exe --version` (tem de ser 3.12.x); se não for, apaga
  a pasta `venv` e recria com `py -3.12 -m venv venv` (secção 1).

---

## 10. Cópias de segurança

### Fazer uma cópia

```powershell
.\scripts\backup.ps1
```

Guarda um ficheiro JSON com utilizadores (e saldos), marcações, movimentos de
créditos, aulas e configuração. Vai por defeito para uma pasta da **OneDrive**
— de propósito: uma cópia guardada no mesmo disco que a base de dados não te
salva de o disco falhar.

Para copiar a base de dados **de produção** (o Railway), define primeiro a
`DATABASE_URL` só nessa janela e usa o `-Producao`:

```powershell
$env:DATABASE_URL = "postgresql://..."
```

```powershell
.\scripts\backup.ps1 -Producao
```

(a `DATABASE_URL` está no Railway, no separador *Variables* do PostgreSQL)

### Quando correr

- **Antes de qualquer coisa que apague** — limpar dados de teste, migrações,
  ações em massa no admin. É a que mais vezes salva.
- De tempos a tempos, assim que houver créditos pagos a sério em jogo.

### Testar o restauro — e porquê

**Uma cópia por testar não é uma cópia.** É a única parte disto que não pode
ser saltada: uma cópia estragada parece perfeitamente normal e só se revela
imprestável no dia em que precisas dela.

Não é conversa: as duas primeiras cópias que este script produziu **não
restauravam**, e ambas pareciam bem. Uma tinha a marca BOM que o PowerShell
acrescenta; a outra tinha os acentos gravados na codificação do Windows em vez
de UTF-8. Só o teste de restauro as apanhou.

O teste faz-se contra uma base de dados de rascunho, **nunca contra a tua**:

```powershell
$env:PYTHONUTF8 = "1"; $env:DATABASE_URL = "sqlite:///C:/Users/Andre/AppData/Local/Temp/teste-restauro.sqlite3"
```

```powershell
python manage.py migrate; python manage.py loaddata "CAMINHO\DA\COPIA.json"
```

Deve dizer `Installed N object(s)`. Depois confirma que os dados lá estão:

```powershell
python manage.py shell -c "from django.contrib.auth import get_user_model as g; print({u.username: u.sessoes_sg for u in g().objects.all()})"
```

No fim, **fecha esse terminal** (ou apaga a variável com
`Remove-Item Env:DATABASE_URL`), senão continuas a trabalhar contra a base de
dados de rascunho sem dar por isso.

### Restaurar a sério

O mesmo `loaddata`, mas sem a `DATABASE_URL` de rascunho — corre contra a base
de dados verdadeira. **Faz uma cópia do estado atual antes**, mesmo que ele
esteja mau: pode ser que o problema não fosse o que pensavas.
