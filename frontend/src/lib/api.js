const json = async (r) => {
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    // A 422 on the instance carries {message, valid}: say the message, not "[object Object]".
    const testo = detail && typeof detail === "object" && !Array.isArray(detail)
      ? detail.message || JSON.stringify(detail) : detail;
    throw new Error(testo || r.statusText);
  }
  return r.json();
};

/** `?instance=<id>`, or nothing for every instance. */
const conIstanza = (url, istanza) =>
  istanza ? `${url}?instance=${encodeURIComponent(istanza)}` : url;

/** The Life instances this operator serves (unreachable ones included, named). */
export const istanze = () => fetch("/api/instances").then(json);
const post = (url, corpo) =>
  fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  }).then(json);

export const elenco = (istanza = "") => fetch(conIstanza("/api/contents", istanza)).then(json);
export const scheda = (id) => fetch(`/api/contents/${encodeURIComponent(id)}`).then(json);
export const decidiLotto = (id, corpo) =>
  post(`/api/contents/${encodeURIComponent(id)}/decision`, corpo);

/** Lo strumento E i suoi utilizzi ancora aperti, in una decisione sola.
 *  Rotta a parte apposta: la cascata e' una scelta, e chi vuole decidere uso
 *  per uso (passando dal lotto, anche per una sola tip) non deve rischiare di
 *  farla per sbaglio. */
export const decidiStrumento = (id, corpo) => post(`/api/strumenti/${id}/decision`, corpo);

/** Tutti gli strumenti ancora aperti di un contenuto, con una domanda sola. */
export const decidiTuttiGliStrumenti = (sourceId, corpo) => post(`/api/contents/${sourceId}/strumenti`, corpo);

/** Un contenuto a capitoli si approva intero: una domanda, un'issue. */
export const decidiPacchetto = (sourceId, corpo) => post(`/api/contents/${sourceId}/pacchetto`, corpo);

export const letture = (sourceId) =>
  fetch(`/api/contents/${sourceId}/letture`).then(json);

export const cambiaEntita = (sourceId, entita) =>
  fetch(`/api/contents/${sourceId}/entita`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entita }),
  }).then(json);

export const repos = () => fetch("/api/repos").then(json);

/** Il materiale che il post consegnava solo a mano: un link o un file.
 *
 *  FormData e non JSON, e senza Content-Type scritto a mano: il confine
 *  multipart lo genera il browser, e fissarlo a mano produce un corpo che il
 *  server non sa dividere. */
export const inviaMateriale = (id, { link, file }) => {
  const corpo = new FormData();
  if (link) corpo.append("link", link);
  if (file) corpo.append("file", file);
  return fetch(`/api/contents/${encodeURIComponent(id)}/materiale`, {
    method: "POST",
    body: corpo,
  }).then(json);
};

export const statoMateriale = (id) =>
  fetch(`/api/contents/${encodeURIComponent(id)}/materiale`).then(json);

/** Il registro esiti: che fine ha fatto ogni strumento adottato. */
export const esiti = (istanza = "") => fetch(conIstanza("/api/esiti", istanza)).then(json);

/** Rilegge le issue su GitHub e aggiorna i record dal commento di chiusura. */
export const sincronizzaEsiti = () =>
  fetch("/api/esiti/sync", { method: "POST" }).then(json);

/** Cio' che rompe «adottata = almeno un'issue vera»: la pagina lo mostra in rosso. */
export const anomalieEsiti = () => fetch("/api/esiti/anomalie").then(json);
