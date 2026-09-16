/*
  Service worker do RESTART NOW.

  Existe por um motivo só: sem um, o telemóvel não oferece "instalar no ecrã
  principal". Não é para pôr a app a funcionar offline.

  **Não guarda páginas.** É deliberado: isto é uma app de marcações. Uma
  página guardada mostraria vagas que já não existem, aulas canceladas e
  saldos errados — e o aluno decidiria com base nisso. Mais vale dizer que
  não há ligação do que mentir com dados de ontem.

  O que guarda são os ficheiros que nunca mudam de conteúdo sem mudar de
  nome: o CSS, os tipos de letra e as imagens da marca. Poupa dados ao aluno
  sem risco nenhum de mostrar informação velha.
*/

const VERSAO = "restart-now-v1";

// Só ficheiros estáticos. Nada de /horario/, /pacotes/ ou do painel.
const PARA_GUARDAR = /\/static\/.*\.(css|js|png|jpg|jpeg|svg|woff2?)$/;

self.addEventListener("install", (evento) => {
  // Entra em vigor sem esperar que as abas antigas fechem.
  self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches
      .keys()
      .then((nomes) =>
        Promise.all(
          nomes.filter((n) => n !== VERSAO).map((n) => caches.delete(n))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (evento) => {
  const pedido = evento.request;

  // Tudo o que não for um GET de ficheiro estático vai à rede, sempre.
  if (pedido.method !== "GET" || !PARA_GUARDAR.test(new URL(pedido.url).pathname)) {
    return;
  }

  evento.respondWith(
    caches.match(pedido).then((guardado) => {
      if (guardado) return guardado;
      return fetch(pedido).then((resposta) => {
        // Só se guarda o que veio bem e do nosso próprio site.
        if (resposta.ok && resposta.type === "basic") {
          const copia = resposta.clone();
          caches.open(VERSAO).then((cache) => cache.put(pedido, copia));
        }
        return resposta;
      });
    })
  );
});
