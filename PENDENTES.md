# Pendentes — decisões e informações em falta

> Lista viva do que está à espera de decisão (nossa ou do Sérgio) para não se
> perder nada. Riscar/apagar à medida que se resolve.

## Pacotes — à espera de reunião com o Sérgio

2. **Conteúdo real dos pacotes** — nomes, nº de sessões, preços E **tipo de
   crédito** (SG/PT/Hybrid) finais. Os atuais são provisórios: "Hybrid" tem 8
   sessões por palpite e o "Pack Experimenta" é fictício (serviu para testes).
   Também confirmar o `credit_type` de cada Tipo de Serviço no admin (agora
   todos ficaram Small Group por defeito, exceto o "PT Individual" de teste).

3. **Natureza do "Hybrid"** — o André ia clarificar com o Sérgio se é mesmo um
   3º tipo isolado (é o que está implementado) ou se tem regra especial.
3. **Mensagens de WhatsApp personalizadas por pacote** — o campo existe no
   admin (`Pack.whatsapp_message`); agora usa a mensagem genérica. O Sérgio
   deve escrever as dele (pode ficar para a formação).
4. **WhatsApp Business (app gratuita)** — recomendação a passar ao Sérgio:
   instalar no número dele (mantém o uso normal) e configurar a *saudação
   automática* + *respostas rápidas* com a informação dos pacotes.
   Automação a sério (API oficial) fica como upgrade futuro: tem custos de
   infraestrutura e prende o número à API — não compensa à escala atual.
   Complemento: pôr toda a informação relevante nos cartões do site, para o
   WhatsApp servir só para fechar a venda.

## A confirmar com o Sérgio (construído com o padrão do setor entretanto)

Decisão de ago 2026: não esperar por ele para avançar. Construímos com o que a
maioria dos estúdios faz e deixamos cada uma fácil de inverter no admin. Ele
confirma na demonstração.

- **Lista de espera** — quando abre vaga, o próximo da fila entra
  automaticamente e gasta 1 crédito (padrão do setor, e o que melhor aproveita
  a vaga). A alternativa é reservar-lhe a vaga X horas à espera de
  confirmação, o que exige avisos que a app não sabe mandar. Ao entrar na
  fila, o aluno lê "se abrir vaga, ficas inscrito e gastas 1 sessão".
- **Faltar sem avisar perde o crédito?** Assumido que sim — é o que faz as
  pessoas cancelarem a tempo e libertarem a vaga, e é o comportamento atual do
  código (marcar falta não devolve nada).
- **Créditos expiram?** Assumido que não, como está hoje.

## DECIDIDO (set 2026): a app junta, o Sérgio avisa

O André decidiu o canal de avisos: **a app não tenta falar com o aluno**.
Quando há alguém para avisar, junta-o num ecrã do painel e o Sérgio manda a
mensagem pelo WhatsApp dele. Mantém o toque pessoal — que é o negócio dele —
e não acrescenta infraestrutura nenhuma.

Já aplicado na **lista de espera** (ecrã "Lista de espera", filtrado por
quem falta avisar). É o padrão a seguir para os lembretes.

Também decidido:
- **O Sérgio é administrador prático mas não mexe em contas de admin.**
  Feito: a lista não lhe mostra os admins, a ficha e a remoção recusam, e os
  campos `is_staff`/`is_superuser` não aparecem no formulário.
- **O aluno não apaga a conta sozinho** — pede ao Sérgio, que apaga no
  painel. Evita que alguém se apague por engano e perca créditos pagos.

## Nota histórica: por onde é que a app avisa o aluno

Levantado em set 2026, ao planear a lista de espera, as presenças e os
lembretes. **A app não tem forma de ir ter com ninguém**: não há email (foi
dispensado de propósito), não há WhatsApp na app (decisão fechada) e não há
notificações. Ela só fala com o aluno quando ele abre o site.

Isto trava duas das três coisas pedidas:

- **Lista de espera** — abre uma vaga às 22h, a app inscreve o próximo e
  gasta-lhe um crédito. Ele só descobre se abrir o site; se não abrir, falta
  a uma aula que não sabia que tinha e perde o crédito.
- **Lembretes** — um lembrete é, por definição, ir ter com a pessoa. Sem
  canal, seria um aviso no site que ela só vê se lá for.

**Resolvido** na secção acima: escolheu-se a opção 1 — o Sérgio avisa pelo
WhatsApp, a partir de um ecrã que lhe diz quem avisar. A alternativa que foi
posta de lado era uma janela de confirmação na lista de espera (a vaga
reservada X horas à espera que o aluno confirme), que continuava a precisar
de alguém que o avisasse.

## Contas de administração (set 2026) — FEITO

Dois administradores: o André para manutenção e o Sérgio como administrador
prático. **As regras já estão no código**: a lista não mostra os admins a
quem não é superuser, a ficha e a remoção recusam, e os campos
`is_staff`/`is_superuser` desaparecem do formulário — dar `is_staff` a um
aluno seria criar um administrador pela porta do lado.

O que fica por fazer é só **a comodidade**: atribuir esse acesso passa hoje
pelo painel de permissões do Django, denso e em inglês. Se um dia for preciso
com frequência, vale um ecrã próprio. Não bloqueia nada.

## Extras / polimento (nada disto bloqueia o lançamento)

- **Ícone do PWA a 512px está ampliado.** Os ícones de instalação no
  telemóvel (`static/img/brand/icon-*.png`) foram gerados a partir do
  `favicon.png`, que é 256×256. O de 192 vem de uma redução e fica nítido;
  o de 512 é uma ampliação e tem as curvas ligeiramente serrilhadas. Vê-se
  pouco (a 512 o ícone só aparece no ecrã de arranque), mas resolve-se de
  vez com o **logótipo em SVG ou numa resolução maior** — com isso, regerar
  é um comando. Falta ao André arranjar o original com o Sérgio ou com quem
  desenhou a marca.
- **Tempo dos testes** — passou de ~2 para ~7 minutos (set 2026). Parte é o
  triplo de testes; parte é a cache ter passado para a base de dados, que é
  mais lenta do que a memória. Se incomodar, a saída é os testes usarem a
  cache de memória (com o teste que guarda essa decisão a ser adaptado).
- **O aluno não vê o próprio histórico** — só o Sérgio o vê, no painel. Não
  é lacuna legal (o RGPD aceita resposta a pedido), mas é a pergunta natural
  a seguir. Por decidir.

## Outros pendentes

- **`SERGIO_WHATSAPP` no Railway** — o número real do Sérgio é
  **`351913621166`** (+351 913 621 166), dado pelo André em set 2026. Põe-se
  na variável de ambiente do Railway, **não** no código: o valor por omissão
  em `settings.py` continua a ser o número de TESTE do André, de propósito.
  Se o real fosse o default, cada aula de teste, cada clique num botão de
  pacote e cada demonstração local mandariam mensagens verdadeiras ao
  Sérgio. O sítio onde o número real tem de estar é a produção, e é lá que
  a app o exige (recusa arrancar sem ele).
- **Política de privacidade (RGPD): falta UMA das três variáveis.**
  - `RGPD_RESPONSAVEL` — **por obter.** O nome ou a empresa do Sérgio, como
    se identifica legalmente. É a única pergunta que o André lhe vai fazer
    (set 2026). Tem de vir dele: o responsável legal pelos dados é o dono do
    negócio, não quem fez a app.
  - `RGPD_CONTACTO` — **`351913621166`**, o WhatsApp dele. Não tem de ser um
    email; o que a lei quer é uma forma real de o aluno pedir para ver ou
    apagar os dados, e o WhatsApp é o canal deste negócio.
  - `RGPD_PRAZO_ANOS` — **2**, decidido pelo André (set 2026). É o intervalo
    habitual para dados de ex-clientes: chega para o aluno voltar sem perder
    o histórico, e não guarda dados de quem desapareceu há muito.
- **Deploy no Railway** — passo a passo em `DEPLOY.md`. O código está
  pronto; falta a parte de painel (conta, PostgreSQL, variáveis). Vai ser
  tratado com o Sérgio, que é quem paga o alojamento.
  *(O throttle atrás de proxy, que estava aqui como pendente, já foi feito.)*
- **Limpar dados de teste antes do deploy** — o André pediu para esperar
  (set 2026). A lista completa está no `CLAUDE.md`, secção 11.
- **Programa semanal**: os 23 encaixes estão todos em "Aula de Grupo" /
  Estúdio por defeito. O Sérgio deve rever o tipo e o local de cada um antes
  de o usar a sério, e o número real de aulas por horário (varia semana a
  semana). *(Os dois encaixes de Segunda que estavam como "PT Individual"
  com 12 lugares foram corrigidos para Aula de Grupo em set 2026.)*
- **Mini-guia do admin para o Sérgio** (formação de entrega).

## Decisões fechadas (não fazer)

- **O programa semanal fica em DUAS páginas** (set 2026). Chegou a equacionar-se
  fundir tudo numa só — editar na lista e gerar dali — por a segunda página
  repetir a tabela da primeira. Decidiu-se manter separado, porque as duas
  fazem coisas diferentes e fundi-las apagava essa diferença:
  - **Programa semanal (a lista)** é o *preset*. O que se muda aqui vale para
    **todas as semanas** geradas daqui para a frente.
  - **Gerar aulas da semana** são os ajustes **daquela semana**. O preset não
    é tocado; na semana seguinte volta tudo aos valores da lista.

  A exceção pontual (chuva, uma aula que muda de sítio só naquele dia) faz-se
  na lista de **Sessões**, que é editável em linha.
- **O gerador da semana NÃO apaga aulas** (ago 2026). Chegou a ser equacionado
  um "gerar por cima" que apagasse a aula existente e criasse outra no lugar.
  Apagar uma `Session` leva as marcações atrás em cascata e devolve os
  créditos a toda a gente — desinscrevia os alunos **em silêncio**, porque não
  há canal de avisos. Seria também reintroduzir a armadilha que levou a tornar
  o cancelamento individual e com confirmação. Em vez disso, a página tem uma
  opção de **atualizar** as aulas existentes, que mantém as inscrições. Para
  destruir uma aula existe o botão "Cancelar esta aula", que devolve os
  créditos como deve ser.
- **Duplicados: compara-se só o instante** (ago 2026, "opção A"). Duas aulas
  diferentes no mesmo instante passam a ser impossíveis de gerar — a segunda é
  tratada como já existente. Foi escolha consciente, por simplicidade. Se um
  dia o Sérgio precisar de duas aulas à mesma hora (ex.: um PT no estúdio e
  uma aula de grupo no parque às 19:00), a solução é a `Session` guardar de
  que encaixe nasceu (um campo novo e uma migração).

- **Preços NÃO aparecem no site** (ago 2026) — quem quiser comprar é
  encaminhado para o WhatsApp, onde o Sérgio faz a venda de forma orgânica e
  com margem para negociar. O campo `Pack.price` fica no admin para uso
  interno dele, mas o template `packages.html` nunca o mostra. Há um teste
  que o garante (`PrecosEscondidosTests`).
- **Avisos ao aluno = na app + WhatsApp manual** (ago 2026) — nada de email,
  SMS ou push. Quando uma aula é cancelada, a marcação fica assinalada em "As
  minhas marcações" e o admin dá ao Sérgio um botão que abre o WhatsApp já com
  a lista dos alunos afetados. Sem custos por mensagem e encaixa no que ele já
  faz todos os dias.
- **Admin sem tema de terceiros, mas refinado** (ago 2026) — mantém-se a
  decisão de não instalar pacotes de tema (django-unfold e afins). O admin vai
  ser modernizado com CSS nosso, mantendo a distinção visual face ao site: o
  site é o cartaz escuro da marca, o admin é uma ferramenta de trabalho clara.
- **Sem lembrete automático de aniversários** — fica só o filtro manual
  "Faz anos hoje" no admin.
- **Sem pagamentos online** — a compra é pelo WhatsApp e o Sérgio soma os
  créditos à mão.
- **Sem integração de WhatsApp na app** — a app WhatsApp Business (grátis,
  oficial, não arrisca o número) é uma opção só para uso do Sérgio, à parte
  do código.
- **`ClientPack` apagado de todo** (jul 2026).
