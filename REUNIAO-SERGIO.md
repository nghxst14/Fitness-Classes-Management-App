# Apresentação ao Sérgio — guião

**Para o André.** O que preparar, o que mostrar e por que ordem, o que dizer em
cada momento, e as respostas que tens de trazer de lá.

> **Mostrar não é o objetivo — é o meio.** A app está construída e testada. O
> que falta são decisões que só o Sérgio pode tomar, e cada uma delas está a
> travar trabalho. A demonstração serve para ele perceber o que está a decidir.
> Leva a secção 4 aberta e vai anotando.

---

## 1. Antes de sair de casa

Uns 15 minutos, **no próprio dia**.

1. **Muda a password do `admin`.** Está em `a12345`, que serviu para
   experimentares. Enquanto o túnel estiver aberto, o painel fica acessível a
   quem tenha o endereço.

2. **Gera as aulas da semana**, mas só se fores mostrar o horário já
   preenchido. Se quiseres gerar à frente dele — que é mais forte —, deixa
   vazio e avisa-o de que é isso que vais fazer.

3. **Liga o portátil à corrente e desliga a suspensão.** O túnel morre quando o
   computador suspende. Se suspender a meio, o site desaparece à frente dele.

4. **Levanta o túnel e testa tu primeiro.**

   ```
   .\scripts\demonstracao.ps1
   ```

   O script só devolve o endereço depois de confirmar que responde. Ainda
   assim, **abre-o no teu telemóvel antes de sair**: entra como aluno, reserva
   uma aula, cancela. Dois minutos que evitam descobrir um problema à frente
   do cliente.

5. **Leva os dois telemóveis a carregar** — o teu, para o lado do aluno, e
   deixa o dele livre para instalar a app no fim.

---

## 2. O que mostrar, e por que ordem

Primeiro o que o **aluno** vê, depois o **painel** dele. A ordem não é
acidental: é o lado do aluno que o faz querer a app; o painel é trabalho que
ele vai ter, e mostrado primeiro parece só isso.

Conta com 30 a 40 minutos. Se tiveres menos, corta a partir do ponto 10 — o
essencial está até lá.

### O lado do aluno (10 min)

1. **O horário, no telemóvel.** Não no teu portátil: é num telemóvel que os
   alunos dele vão usar isto. Mostra os quatro estados numa vista só — uma
   aula reservável, uma cheia, uma já reservada e uma que já decorreu.

2. **A vista de semana.** O botão "Ver a semana" mostra os sete dias de uma
   vez. É o que evita andar de seta em seta para marcar a semana toda.

3. **Reservar.** *O momento que vende.* O contador de saldos no topo desce
   **sem a página recarregar**, e o botão muda para "Reservado" ali mesmo.

4. **Cancelar**, em "As minhas marcações" — e o crédito a voltar. É a pergunta
   que ele vai fazer de certeza.

5. **Uma aula cheia → lista de espera.** Mostra que entrar na fila **não gasta
   créditos**, e diz a frase que interessa:
   > *"Se abrir uma vaga, o primeiro da fila fica inscrito e gasta a sessão. A
   > app não manda mensagens a ninguém — aparece-te no painel quem tens de
   > avisar."*

   É aqui que se confirma a decisão nº 5 da secção 4.

6. **Pacotes → WhatsApp.** Sem preços, como ele pediu. Carrega no botão e
   mostra a mensagem já escrita a abrir na conversa dele. É onde percebe que a
   app não lhe tira a venda das mãos.

7. **Instalar no telemóvel.** No fim desta parte, no telemóvel **dele**: menu
   do browser → *Adicionar ao ecrã principal*. Fica com o ícone e abre como
   uma app. Diz que não é uma app da loja — é o site, mais bem embrulhado.

### O painel dele (15 min)

8. **A página de entrada.** As últimas atividades, à direita. Explica para que
   serve com o caso concreto:
   > *"A meio de atualizares os créditos do mês, se não te lembrares se já
   > deste os da Joana, está aqui — com o valor."*

9. **Gerar as aulas da semana.** *O ecrã que vai usar todas as semanas.* Mostra
   que ajusta o tipo, o local e a lotação **antes** de gerar, e que o programa
   semanal fica intacto. **Gera uma semana à frente dele** e volta ao horário
   para ele ver as aulas a aparecer.

10. **Somar créditos a um aluno.** O gesto que vai repetir depois de cada
    pagamento: na lista, escreve o número, grava. Faz um à frente dele.

11. **O histórico do aluno.** Logo a seguir, abre o histórico dessa pessoa e
    mostra a linha que o teu ajuste acabou de criar.
    > *"Quando uma aluna disser que comprou 10 e só foi a 3, é aqui que vês o
    > que aconteceu de verdade — quem deu, quando, e quanto."*

    É a funcionalidade que ele não sabe que precisa até precisar. Não a saltes.

12. **Marcar presenças.** Abre uma aula passada e mostra os botões por aluno.
    Diz que é para usar com o telemóvel na mão no fim da aula, e que **não
    mexe em créditos nenhuns**.

13. **Aulas de amanhã.** O botão no topo das Sessões: quem tem aula amanhã,
    com o número a abrir o WhatsApp. Mesmo princípio da lista de espera — a
    app junta a informação, o aviso é dele.

14. **Password provisória.** Abre a ficha de um aluno e carrega no botão.
    > *"Quando alguém te disser que se esqueceu da password, é um clique. Sai
    > um código, e tens ali o botão para lho mandar pelo WhatsApp. Ele é
    > obrigado a escolher outra quando entrar — tu nunca ficas a saber a
    > password dele."*

### O que fica por dizer (5 min)

15. **A política de privacidade.** Mostra-lhe a página e diz-lhe que o nome
    dele está lá como responsável, porque é dele a responsabilidade legal
    pelos dados dos alunos. Não é preciso mais do que um minuto, mas ele deve
    saber que aquilo existe e porquê.

---

## 3. O que **não** prometer

Coisas que não existem. Se ele perguntar, a resposta honesta é *"dá para
fazer, ainda não está feito"* — nunca *"sim, tem"*.

- **A app não avisa ninguém, de todo.** Não há email, não há mensagens
  automáticas. Quando uma aula é cancelada o crédito volta certo, mas quem
  avisa os alunos é ele. O mesmo para a lista de espera e para os lembretes: a
  app **junta a informação num ecrã**, o envio é dele. Isto é o mais
  importante de deixar claro — é a diferença entre ele confiar na app e ficar
  a achar que ela falhou.
- **Não há pagamentos online.** Decidido, não esquecido.
- **Os alunos não veem o próprio histórico.** Só ele, no painel.
- **Não há relatórios nem estatísticas** (quantas aulas cheias, quem faltou
  mais). Dá para fazer quando houver dados que cheguem para valer a pena.
- **Só funciona com números portugueses.** Nove dígitos a começar por 9.

E o que está **decidido não fazer**: pagamentos online, integração de WhatsApp
por API, vários treinadores, app nativa nas lojas. Se ele pedir, não é dizer
que não dá — é explicar porque não compensa **à escala dele**, e que a decisão
pode ser revista se o negócio crescer.

---

## 4. As respostas a trazer

As quatro primeiras impedem qualquer aluno real de entrar. **Traz estas, nem
que não tragas mais nenhuma.**

| # | Pergunta | O que trava |
|---|---|---|
| 1 | **Quais são os pacotes a sério?** Nome, número de sessões e a que tipo de crédito dão. Os que estão no site são inventados. | Impede alunos |
| 2 | **O que é exatamente o "Hybrid"?** Está construído como um terceiro tipo isolado, com saldo próprio. Se na cabeça dele for outra coisa, é melhor saber agora. | Impede alunos |
| 3 | **Cada tipo de aula gasta que crédito?** Ficaram todos em Small Group por defeito. Se estiver errado, os alunos gastam o balde errado e depois corrige-se aluno a aluno. | Impede alunos |
| 4 | **Aceita pagar o alojamento?** Cerca de 5 a 12 EUR/mês, no cartão dele. **Não deixes para o fim** — é a conversa que se adia com mais facilidade. | Impede o deploy |
| 5 | **Lista de espera: está bem assim?** Quando abre vaga, o primeiro da fila entra e gasta o crédito, e aparece-lhe no painel para avisar. Está construído assim — confirma. | Confirmar |
| 6 | **Quem falta sem avisar perde o crédito?** É o que quase todos os estúdios fazem, e é o que faz as pessoas cancelarem a tempo. Está construído assim. | Confirmar |
| 7 | **Até quanto tempo antes pode o aluno cancelar?** Hoje está **sem limite** em todas as aulas. Pode ser diferente por tipo (ex.: 12h no PT, livre nas de grupo). | Regra de negócio |
| 8 | **Os créditos expiram?** Estão construídos para não expirar. Se quiser validade, muda bastante coisa. | Regra de negócio |
| 9 | **O programa semanal está certo?** Os 23 encaixes têm os horários dele, mas o tipo e o local ficaram todos por defeito. Revê com ele, encaixe a encaixe. | Regra de negócio |
| 10 | **Tem o logótipo em ficheiro grande ou vetorial?** O ícone da app no telemóvel foi ampliado de uma imagem pequena e nota-se. Com o original, resolve-se num minuto. | Detalhe |

**Já respondidas — não voltes a perguntar:**
o número de WhatsApp dele (`351 913 621 166`), o nome para a política de
privacidade (Sérgio Luís Marques e Silva Paulo), e o prazo de conservação dos
dados (2 anos).

---

## 5. Depois: o deploy

Só quando ele disser sim ao alojamento. O passo a passo está no `DEPLOY.md`;
aqui fica a ordem.

1. **Conta no Railway, projeto a partir do GitHub, PostgreSQL** — passos 1 a 3
   do `DEPLOY.md`. O primeiro deploy vai falhar; é normal, faltam as variáveis.

2. **Gera o domínio primeiro, as variáveis depois.** É a ordem que confunde
   toda a gente: só sabes o endereço depois de o Railway o gerar, e duas das
   variáveis precisam dele. *Settings → Networking → Generate Domain*.

3. **As oito variáveis**, em tabela no `DEPLOY.md`. Quatro delas — o número do
   Sérgio e as três do RGPD — **são obrigatórias**: a app recusa arrancar sem
   elas, de propósito. Se o deploy falhar, lê a mensagem: ela diz qual falta.

4. **Cria o superuser — e não lhe chames "admin".** Usa o telemóvel do Sérgio
   como nome de utilizador, e uma password a sério (a de demonstração não).

5. **Liga as cópias de segurança e testa um restauro** — antes de haver
   créditos pagos. Procedimento no `GUIA_COMANDOS.md`, secção 10. Uma cópia
   por testar não é uma cópia: as duas primeiras que este projeto produziu não
   restauravam, e pareciam bem.

6. **Mete os dados verdadeiros**, com as respostas da reunião: pacotes, tipos
   de serviço, e o programa semanal revisto.

> **E só então os alunos.** A política de privacidade e o consentimento no
> registo já estão feitos — o que falta é o conteúdo real dos pacotes. Enquanto
> isso não estiver certo, o site fica de pé só para vocês os dois.

---

*O `MANUAL.md` é o documento equivalente para o Sérgio — esse é para ele levar.*
