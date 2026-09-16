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

## Decidir ANTES de construir: por onde é que a app avisa o aluno

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

Saídas em aberto (por decidir com o André):
1. **O Sérgio avisa pelo WhatsApp**, a partir de um ecrã que lhe diz quem
   avisar. Mantém o toque pessoal, que é o negócio dele, e não precisa de
   infraestrutura nenhuma.
2. **Janela de confirmação** na lista de espera: a vaga fica reservada X
   horas à espera que o aluno confirme, em vez de o inscrever logo.

## Contas de administração (set 2026)

Decisão do André: vai haver **dois** administradores — ele para manutenção e
o Sérgio como administrador prático — e, mais tarde, um admin poderá dar
acesso a outro utilizador.

O que falta desenhar (o código assume hoje **um** superuser, e o
`accounts/admin.py` esconde grupos e permissões por causa disso):
- o que o Sérgio **pode** e **não pode** fazer (dar créditos e cancelar aulas,
  de certeza; apagar alunos? mudar passwords? criar outros admins?);
- um ecrã para atribuir esse acesso que não seja o painel de permissões do
  Django — dezenas de checkboxes técnicas em inglês, o oposto de simples.

## Outros pendentes

- **Trocar `SERGIO_WHATSAPP`** em `config/settings.py` pelo número real do
  Sérgio (agora está o número de teste do André).
- **Dados da política de privacidade (RGPD)** — as variáveis
  `RGPD_RESPONSAVEL`, `RGPD_CONTACTO` e `RGPD_PRAZO_ANOS`. **Só o Sérgio as
  pode dar** (é ele o responsável legal pelos dados dos alunos) e a app
  recusa arrancar em produção sem elas. É a pergunta 7 do
  `REUNIAO-SERGIO.md`: como se identifica legalmente, para onde escrevem os
  alunos a pedir os dados ou o apagamento, e quanto tempo os guarda depois
  de alguém deixar de ser aluno.
- **Deploy (Bloco 5)**: Railway ou PythonAnywhere; PostgreSQL; `DEBUG=False`;
  whitenoise; e rever o throttle do login (atrás de proxy, o `REMOTE_ADDR`
  passa a ser o IP do proxy — usar o cabeçalho correto).
- **Limpar dados de teste antes do deploy** — utilizadores User1/User2/User3
  e Ana Teste (913000001), aulas de teste e pacotes fictícios.
- **Programa semanal**: o preset (23 encaixes) está pré-preenchido com tudo em
  "Aula de Grupo" (Small Group) / Estúdio por defeito. O Sérgio deve rever o
  tipo e o local de cada encaixe no admin (Programa semanal) antes de o usar
  a sério, e o número real de aulas por horário (varia semana a semana).
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
