import { useCallback, useEffect, useState } from "react";
import {
  scheda as leggiScheda,
  decidiLotto,
  decidiStrumento,
  decidiTuttiGliStrumenti,
  decidiPacchetto,
  cambiaEntita,
  inviaMateriale,
  statoMateriale,
} from "../lib/api";

/** Carica una scheda e decide sulle sue tip, una alla volta o a cascata.
 *
 *  Dopo una decisione la scheda si ridisegna dalla RISPOSTA, mai dallo stato
 *  locale: il backend decide e restituisce cio' che e' successo davvero
 *  (cascata compresa), quindi indovinare qui mostrerebbe una schermata che il
 *  server non ha mai confermato — ed e' proprio la cascata, dove una
 *  decisione ne chiude cinque, a rendere l'ipotesi piu' facile da sbagliare.
 */
export function useScheda(sourceId) {
  const [scheda, setScheda] = useState(null);
  const [caricamento, setCaricamento] = useState(false);
  const [errore, setErrore] = useState(null);
  const [problemi, setProblemi] = useState([]);
  const [issueUrls, setIssueUrls] = useState([]);
  const [inCorso, setInCorso] = useState(false);
  const [lavoro, setLavoro] = useState(null);

  const ricarica = useCallback(async () => {
    if (!sourceId) return;
    setCaricamento(true);
    setErrore(null);
    try {
      setScheda(await leggiScheda(sourceId));
    } catch (e) {
      setErrore(e.message || "errore sconosciuto");
    } finally {
      setCaricamento(false);
    }
  }, [sourceId]);

  useEffect(() => {
    setScheda(null);
    setProblemi([]);
    setIssueUrls([]);
    setLavoro(null);
    ricarica();
  }, [ricarica]);

  // Lo stato di una ri-estrazione gia' avviata: esiste anche se la pagina e'
  // stata chiusa e riaperta, perche' vive in un file e non in questa scheda.
  useEffect(() => {
    if (!sourceId) return;
    statoMateriale(sourceId).then(setLavoro).catch(() => setLavoro(null));
  }, [sourceId]);

  // Nessuno avvisa quando il sottoprocesso finisce: si chiede. Ogni dieci
  // secondi e SOLO mentre e' in corso — un'attesa che interroga per sempre e'
  // un carico costante su una pagina che di solito non aspetta niente.
  useEffect(() => {
    if (lavoro?.stato !== "in_corso" || !sourceId) return undefined;
    const timer = setInterval(async () => {
      try {
        const adesso = await statoMateriale(sourceId);
        setLavoro(adesso);
        // Le tip nuove sono gia' in coda: la scheda va riletta, non indovinata.
        if (adesso?.stato && adesso.stato !== "in_corso") ricarica();
      } catch {
        // Una lettura di stato fallita non dice niente sul lavoro: si ritenta
        // al giro dopo invece di dichiararlo morto.
      }
    }, 10000);
    return () => clearInterval(timer);
  }, [lavoro?.stato, sourceId, ricarica]);

  const applica = useCallback(async (chiamata) => {
    setErrore(null);
    setInCorso(true);
    try {
      const { problemi: nuovi = [], issue_urls: urls = [], ...aggiornata } =
        await chiamata();
      setScheda(aggiornata);
      setProblemi(nuovi);
      // Accumulate: una scheda si decide in piu' passaggi, e azzerare qui
      // farebbe sparire il link dell'issue appena aperta al primo clic dopo.
      setIssueUrls((prima) => [...prima, ...urls]);
      return true;
    } catch (e) {
      setErrore(e.message || "errore sconosciuto");
      // A refused adoption can still have settled other tips of the batch:
      // redraw from the server without clearing the message just set.
      if (sourceId) leggiScheda(sourceId).then(setScheda).catch(() => {});
      return false;
    } finally {
      setInCorso(false);
    }
  }, [sourceId]);

  return {
    scheda,
    caricamento,
    errore,
    problemi,
    issueUrls,
    inCorso,
    ricarica,
    // Una tip sola passa comunque dal LOTTO, con un id solo: e' l'unica
    // rotta che risponde con la scheda aggiornata, e ridisegnare da quella
    // e' il punto. `/api/proposals/{id}/decision` risponde con l'esito e
    // basta — giusto per la CLI, inservibile per una pagina che si ridisegna.
    decidiUnaTip: useCallback(
      (id, { verdict, ...resto }) =>
        applica(() =>
          decidiLotto(sourceId, {
            adotta: verdict === "adopted" ? [id] : [],
            scarta: verdict === "rejected" ? [id] : [],
            ...resto,
          }),
        ),
      [applica, sourceId],
    ),
    cambiaLEntita: useCallback(
      async (entita) => setScheda(await cambiaEntita(sourceId, entita)),
      [sourceId],
    ),
    decidiIlPacchetto: useCallback(
      (corpo) => applica(() => decidiPacchetto(sourceId, corpo)),
      [applica, sourceId],
    ),
    lavoro,
    mandaMateriale: useCallback(
      async (materiale) => {
        const avviato = await inviaMateriale(sourceId, materiale);
        setLavoro(avviato);
        return avviato;
      },
      [sourceId],
    ),
    decidiTuttiStrumenti: useCallback(
      (corpo) => applica(() => decidiTuttiGliStrumenti(sourceId, corpo)),
      [applica, sourceId],
    ),
    decidiUnoStrumento: useCallback(
      (id, corpo) => applica(() => decidiStrumento(id, corpo)),
      [applica],
    ),
  };
}
