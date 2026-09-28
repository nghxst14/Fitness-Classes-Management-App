/*
  A janela da password provisória, no painel.

  Substitui dois `confirm()` e um aviso no topo da página: o do browser não
  se pode desenhar nem escrever em condições, e o aviso obrigava a recarregar
  a página e a selecionar a password à mão para a copiar.

  Sem este ficheiro nada se parte — o formulário submete à moda antiga e a
  password aparece num aviso. É por isso que o botão continua a ser um
  submit a sério e não um <div> com um onclick.
*/
(function () {
  "use strict";

  var janela = document.getElementById("janela-password");
  var formulario = document.getElementById("gerar-password-provisoria");
  if (!janela || !formulario) return;

  var botaoDaFicha = document.querySelector(
    'button[form="gerar-password-provisoria"]'
  );
  var passoConfirmar = janela.querySelector('[data-passo="confirmar"]');
  var passoResultado = janela.querySelector('[data-passo="resultado"]');
  var caixaPassword = janela.querySelector("#password-gerada");
  var botaoCopiar = janela.querySelector("[data-copiar]");
  var ligacaoWhatsApp = janela.querySelector("[data-whatsapp]");
  var focoAnterior = null;

  function abrir() {
    focoAnterior = document.activeElement;
    passoConfirmar.hidden = false;
    passoResultado.hidden = true;
    janela.hidden = false;
    janela.querySelector("[data-gerar]").focus();
    document.addEventListener("keydown", aoTeclar);
  }

  function fechar() {
    janela.hidden = true;
    document.removeEventListener("keydown", aoTeclar);
    // Devolve o foco a quem abriu a janela: sem isto, quem navega por
    // teclado é atirado para o início da página.
    if (focoAnterior) focoAnterior.focus();
  }

  function aoTeclar(evento) {
    if (evento.key === "Escape") fechar();
  }

  function gerar() {
    var botao = janela.querySelector("[data-gerar]");
    botao.disabled = true;
    botao.textContent = "A gerar...";

    fetch(formulario.action, {
      method: "POST",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      body: new FormData(formulario),
    })
      .then(function (resposta) {
        if (!resposta.ok) throw new Error(resposta.status);
        return resposta.json();
      })
      .then(function (dados) {
        caixaPassword.value = dados.password;
        if (dados.whatsapp) {
          ligacaoWhatsApp.href = dados.whatsapp;
          ligacaoWhatsApp.hidden = false;
        } else {
          // Contas sem telemóvel (staff) não têm conversa para abrir.
          ligacaoWhatsApp.hidden = true;
        }
        passoConfirmar.hidden = true;
        passoResultado.hidden = false;
        caixaPassword.focus();
        caixaPassword.select();
      })
      .catch(function () {
        // Se algo falhar, submete à moda antiga em vez de deixar o Sérgio
        // sem saber se a password mudou ou não.
        formulario.submit();
      })
      .finally(function () {
        botao.disabled = false;
        botao.textContent = "Gerar";
      });
  }

  function copiar() {
    caixaPassword.select();
    var feito = function () {
      botaoCopiar.textContent = "Copiado";
      setTimeout(function () {
        botaoCopiar.textContent = "Copiar";
      }, 1500);
    };
    // A API moderna só existe em HTTPS e em localhost; o execCommand é o
    // recurso para os outros casos (e para browsers mais antigos).
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(caixaPassword.value).then(feito, function () {
        document.execCommand("copy");
        feito();
      });
    } else {
      document.execCommand("copy");
      feito();
    }
  }

  if (botaoDaFicha) {
    botaoDaFicha.addEventListener("click", function (evento) {
      evento.preventDefault(); // não submete: a janela é que trata disto
      abrir();
    });
  }
  janela.querySelector("[data-gerar]").addEventListener("click", gerar);
  botaoCopiar.addEventListener("click", copiar);
  janela.querySelectorAll("[data-fechar]").forEach(function (botao) {
    botao.addEventListener("click", fechar);
  });
  // Clicar fora da caixa fecha; clicar dentro não.
  janela.addEventListener("click", function (evento) {
    if (evento.target === janela) fechar();
  });
})();
