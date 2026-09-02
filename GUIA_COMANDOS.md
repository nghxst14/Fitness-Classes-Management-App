# Guia de comandos — Gestão de Treinos

Referência dos comandos que vais usar neste projeto, com uma descrição do que
cada um faz. Corre-os no **PowerShell**, dentro da pasta do projeto
(`...\Gestao de treinos`), com o ambiente virtual ativo (ver secção 1).

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
python -m venv venv
```
Cria o ambiente virtual (só é preciso **uma vez**, no arranque do projeto).

```powershell
venv\Scripts\activate
```
Ativa o ambiente. Tens de fazer isto **sempre que abres um terminal novo** para
trabalhar. Quando está ativo, aparece `(venv)` no início da linha.

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
  endereço**, escreve `powershell` e Enter. Abre já no sítio certo.
- Ou, num terminal qualquer:
  ```powershell
  cd "C:\Users\André\Documents\CLAUDE\Gestao de treinos"
  ```
  Muda para a pasta do projeto (as aspas são precisas por causa dos espaços).

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

## 8. Testar a recuperação de password (em desenvolvimento)

Não é preciso servidor de email. Ao pedir a recuperação, o email com o link é
"enviado" para o **terminal onde corre o `runserver`** — procura lá um bloco de
texto com um link tipo `http://127.0.0.1:8000/conta/reset/...` e abre-o no
browser.

---

## 9. Problemas comuns

- **`python` não é reconhecido** → o Python não está instalado ou não está no
  PATH. Reinstala a partir de python.org e marca "Add Python to PATH".
- **Não aparece `(venv)`** → esqueceste-te de correr `venv\Scripts\activate`.
- **A página dá erro depois de mexer nos modelos** → provavelmente falta correr
  `makemigrations` + `migrate`.
- **O `runserver` diz "That port is already in use"** → já tens um servidor a
  correr noutro terminal, ou usa outra porta: `python manage.py runserver 8001`.
