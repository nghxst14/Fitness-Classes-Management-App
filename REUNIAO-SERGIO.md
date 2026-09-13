# Reunião com o Sérgio — guião

**Para o André.** O que preparar antes, o que mostrar e por que ordem, e — o
mais importante — as doze respostas que tens de trazer de lá.

> **O objetivo desta reunião não é mostrar a app.** É sair de lá com decisões.
> A app está construída, mas há uma dúzia de coisas que só o Sérgio pode
> decidir, e cada uma delas está a travar trabalho. Mostrar serve para ele
> perceber o que está a decidir — não é o fim em si. Leva a lista da secção 3
> aberta e vai anotando. Se saíres com dez das doze respostas, correu bem.

---

## 1. Antes de sair de casa

Uns 15 minutos, **no próprio dia**. Não faças na véspera — os dados de
demonstração envelhecem.

1. **Pede para renovar as aulas de demonstração.** Se forem antigas, o Sérgio
   abre o horário e vê um ecrã vazio: a pior primeira impressão possível.

2. **Confirma que a password do `admin` é longa.** Enquanto o túnel estiver
   aberto, o painel fica acessível a quem tenha o endereço, e é o único login
   sem limite de tentativas.

3. **Liga o portátil à corrente e desliga a suspensão.** O túnel morre quando o
   computador suspende — já aconteceu uma vez, de noite. Se suspender a meio da
   reunião, o site desaparece à frente dele.

4. **Levanta o túnel e testa tu primeiro.**

   ```
   .\scripts\demonstracao.ps1
   ```

   O script só devolve o endereço depois de confirmar que responde. Ainda
   assim, **abre-o no teu telemóvel antes de sair**: entra com a conta de
   aluno, reserva uma aula, cancela. Dois minutos que evitam descobrir um
   problema à frente do cliente.

---

## 2. O que mostrar, e por que ordem

Primeiro o que o aluno vê, depois o painel dele. A ordem não é acidental: é o
lado do aluno que faz o Sérgio querer a app; o painel é trabalho que ele vai
ter, e mostrado primeiro parece só isso.

1. **O horário, no telemóvel dele** — não no teu portátil. Mostra os quatro
   estados numa só vista: uma aula reservável, uma esgotada, uma já reservada e
   uma que já decorreu.

2. **Reservar.** O momento que vende: o contador de saldos no topo desce **sem
   a página recarregar**, e o botão muda para "Reservado" ali mesmo.

3. **Cancelar**, em "As minhas marcações" — e o crédito a voltar. É a pergunta
   que ele vai fazer de certeza.

4. **Pacotes → WhatsApp.** Sem preços, como ele pediu. Carrega no botão e
   mostra a mensagem já escrita a abrir na conversa dele. É aqui que percebe
   que a app não lhe tira a venda das mãos.

5. **Admin: gerar a semana.** O ecrã que vai usar todas as semanas. Mostra que
   ajusta o tipo, o local e a lotação **antes** de gerar, e que o programa
   semanal fica intacto. Gera uma semana à frente dele.

6. **Admin: somar créditos a um aluno.** O gesto que vai repetir depois de cada
   pagamento. Faz um à frente dele.

7. **Admin: o extrato de créditos.** Logo a seguir, mostra a linha que esse
   ajuste acabou de criar. Explica com a frase concreta: *"quando uma aluna
   disser que comprou 10 e só foi a 3, é aqui que vês o que aconteceu de
   verdade."* É a funcionalidade que ele não sabe que precisa até precisar.

---

## 3. As doze respostas a trazer

As quatro primeiras impedem qualquer aluno real de entrar.

| # | Pergunta | O que trava |
|---|---|---|
| 1 | **Quais são os pacotes a sério?** Nome, número de sessões e a que tipo de crédito dão. Os que estão no site são inventados. | Impede alunos |
| 2 | **O que é exatamente o "Hybrid"?** Está construído como um terceiro tipo isolado, com saldo próprio. Se na cabeça dele for outra coisa, é melhor saber agora. | Impede alunos |
| 3 | **Cada tipo de aula gasta que crédito?** Ficaram todos em Small Group por defeito. Se estiver errado, os alunos gastam o balde errado e depois é preciso corrigir aluno a aluno. | Impede alunos |
| 4 | **Segunda às 07:00 e às 08:00 são mesmo PT?** Estão no programa como "PT Individual" com **12 vagas**, o que não faz sentido — é um resto dos testes. | Impede alunos |
| 5 | **Qual é o número de WhatsApp dele?** Com indicativo. Hoje o site tem o número de teste do André. | Impede o deploy |
| 6 | **Aceita pagar o alojamento?** Cerca de 5 a 12 EUR/mês, no cartão dele. **Não deixes esta para o fim** — é a conversa que se adia com mais facilidade. | Impede o deploy |
| 7 | **Dados pessoais: quem responde e por quanto tempo?** Para a política de privacidade: nome/entidade, um contacto, e quanto tempo guardar os dados de quem deixa de ser aluno. É ele o responsável legal. | Impede alunos |
| 8 | **Quem falta sem avisar perde o crédito?** É o que quase todos os estúdios fazem, e é o que faz as pessoas cancelarem a tempo. Está construído assim. | Trava as presenças |
| 9 | **Até quanto tempo antes pode o aluno cancelar?** Hoje está **sem limite** em todas as aulas. Pode ser diferente por tipo (ex.: 12h no PT, livre nas de grupo). | Regra de negócio |
| 10 | **Os créditos expiram?** Estão construídos para não expirar. Se quiser validade, muda bastante coisa. | Regra de negócio |
| 11 | **Lista de espera: entra sozinho ou confirma?** Quando abre vaga numa aula cheia, o próximo entra e gasta o crédito, ou fica-lhe reservada à espera de resposta? | Próxima função |
| 12 | **As aulas de hoje que já passaram: mostrar ou esconder?** Hoje aparecem esbatidas. Mostra-lhe o ecrã e deixa-o decidir — é uma linha de código. | Detalhe |

---

## 4. O que não prometer

Coisas que ainda não existem. Se ele perguntar, a resposta honesta é *"dá para
fazer, ainda não está feito"* — nunca *"sim, tem"*.

- **Avisar o aluno quando uma aula é cancelada.** Hoje o crédito volta certo,
  mas ninguém lhe diz nada. Está decidido como fazer, falta construir.
- **Lista de espera.** Aula cheia é um beco sem saída.
- **Marcar presenças.** O modelo prevê, mas não há ecrã prático.
- **Lembretes antes da aula.** Não há nenhum canal de envio.
- **Histórico do aluno.** Só mostra aulas futuras.
- **Vista de semana** e instalar como app no telemóvel.

E o que está **decidido não fazer**: pagamentos online, integração de WhatsApp
por API, vários treinadores, app nativa. Se ele pedir, não é dizer que não dá —
é explicar porque não compensa **à escala dele**, e que a decisão pode ser
revista se o negócio crescer.

---

## 5. Depois, o deploy

Só quando ele disser sim ao alojamento. O passo a passo completo está no
`DEPLOY.md`; aqui fica a ordem e o que mudou desde que esse guia foi escrito.

1. **Conta no Railway, projeto a partir do GitHub, PostgreSQL** — passos 1 a 3
   do `DEPLOY.md`. O primeiro deploy vai falhar; é normal, faltam as variáveis.

2. **Gera o domínio primeiro, as variáveis depois.** É a ordem que confunde
   toda a gente: só sabes o endereço depois de o Railway o gerar, e duas das
   variáveis precisam dele. Gera em *Settings → Networking → Generate Domain*.

3. **As cinco variáveis.** Estão em tabela no `DEPLOY.md`. **Mudou uma coisa
   importante:** o `SERGIO_WHATSAPP` passou a ser obrigatório — a app agora
   **recusa arrancar** sem ele, em vez de subir a mandar os alunos para o
   número de teste. Se o deploy falhar com essa mensagem, é isso que falta.

4. **Cria o superuser — e não lhe chames "admin".** Metade dos ataques por
   força bruta só experimenta esse nome, e o login do painel ainda não tem
   limite de tentativas. Usa o telemóvel do Sérgio como nome de utilizador.

5. **Liga as cópias de segurança e testa um restauro** — antes de haver
   créditos pagos. Procedimento no `GUIA_COMANDOS.md`, secção 10. Uma cópia por
   testar não é uma cópia: as duas primeiras que este projeto produziu não
   restauravam, e pareciam bem.

6. **Limpa os dados de teste e mete os verdadeiros**, com as respostas da
   reunião. Inclui apagar o superuser `claude-preview`, os alunos de
   demonstração e as aulas marcadas. **Faz uma cópia antes** — apagar em massa
   é precisamente quando isso salva.

> **E só então os alunos.** Entre o site estar no ar e mandares o link faltam
> ainda a política de privacidade, os termos e o consentimento no registo. São
> umas horas de trabalho e dependem das respostas dele. Enquanto isso não
> existir, o site fica de pé só para vocês os dois.

---

*Existe também uma versão em página web deste guião, para consultar no
telemóvel. O `MANUAL.md` é o documento equivalente para o Sérgio.*
