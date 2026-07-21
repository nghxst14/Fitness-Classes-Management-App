# Pendentes — decisões e informações em falta

> Lista viva do que está à espera de decisão (nossa ou do Sérgio) para não se
> perder nada. Riscar/apagar à medida que se resolve.

## Pacotes — à espera de reunião com o Sérgio

1. **Preços visíveis nos cartões?** O campo existe e aparece se preenchido.
   Preço à vista filtra curiosos; preço só na conversa dá margem de negociação.
   Decisão comercial do Sérgio.
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

## Outros pendentes

- **Trocar `SERGIO_WHATSAPP`** em `config/settings.py` pelo número real do
  Sérgio (agora está o número de teste do André).
- **Deploy (Bloco 5)**: Railway ou PythonAnywhere; PostgreSQL; `DEBUG=False`;
  whitenoise; e rever o throttle do login (atrás de proxy, o `REMOTE_ADDR`
  passa a ser o IP do proxy — usar o cabeçalho correto).
- **Lembrete diário de aniversários** — tarefa agendada, só faz sentido
  montar no deploy.
- **Decisão: ClientPack** — apagar de todo (como a app dos vídeos) ou manter
  escondido do admin. Tabela está vazia; recomendação: apagar.
- **Limpar dados de teste antes do deploy** — utilizadores User1/User2/User3
  e Ana Teste (913000001), aulas de teste e pacotes fictícios.
- **Programa semanal**: o preset (23 encaixes) está pré-preenchido com tudo em
  "Aula de Grupo" (Small Group) / Estúdio por defeito. O Sérgio deve rever o
  tipo e o local de cada encaixe no admin (Programa semanal) antes de o usar
  a sério, e o número real de aulas por horário (varia semana a semana).
- **Mini-guia do admin para o Sérgio** (formação de entrega).
