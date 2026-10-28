/** The dashboard's sections. The key is what an esito carries in `categoria`
 *  (written in its issue, read by `sync`); name and line are presentation. */
export const CATEGORIE = [
  {
    key: "modelli",
    nome: "Modelli e gateway",
    descrizione: "quale modello risponde, e come ci si arriva",
  },
  {
    key: "agenti",
    nome: "Agenti e review",
    descrizione: "secondi pareri, revisori, agenti specializzati",
  },
  {
    key: "ingest",
    nome: "Ingestione contenuti",
    descrizione: "leggere pagine, video e reel per estrarne le tip",
  },
  {
    key: "sessioni",
    nome: "Sessioni e sorveglianza",
    descrizione: "tenere d'occhio le sessioni di Claude Code",
  },
  {
    key: "memoria",
    nome: "Memoria e conoscenza",
    descrizione: "brain, idee, conoscenza da libri e documenti",
  },
  {
    key: "metodo",
    nome: "Metodo e regole",
    descrizione: "come lavorano le sessioni: skill di processo e regole",
  },
  {
    key: "org",
    nome: "Organizzazione",
    descrizione: "code di lavoro e priorità",
  },
  {
    key: "marketing",
    nome: "Marketing",
    descrizione: "strumenti del nodo Marketing",
  },
];

/** A record with no category, or one this page does not know yet, still shows:
 *  it lands here, where it is visibly waiting for its card. */
export const SENZA_CATEGORIA = {
  key: "",
  nome: "Senza categoria",
  descrizione: "manca la scheda nell'issue (Categoria:)",
};

export const ETICHETTA_COSTO = {
  gratis: "gratis",
  abbonamento: "abbonamento",
  api: "API a consumo",
};

/** Groups records by category, in the order above; unknown or missing last. */
export function raggruppa(esiti) {
  const note = new Set(CATEGORIE.map((c) => c.key));
  const gruppi = CATEGORIE.map((c) => ({
    ...c,
    esiti: esiti.filter((e) => e.categoria === c.key),
  }));
  const altri = esiti.filter((e) => !note.has(e.categoria));
  if (altri.length) gruppi.push({ ...SENZA_CATEGORIA, esiti: altri });
  return gruppi.filter((g) => g.esiti.length > 0);
}
