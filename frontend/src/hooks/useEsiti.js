import { useCallback, useEffect, useMemo, useState } from "react";
import { anomalieEsiti, esiti as leggiEsiti, sincronizzaEsiti } from "../lib/api";
import { raggruppa } from "../lib/categorie";
import { STATI } from "../lib/stati";

export { STATI };

const norm = (s) => (s || "").toLowerCase();

/** Loads the adoption register and exposes filter, search and sync.
 *  Load error and sync problems are kept apart: a failed sync leaves the
 *  list readable, and must not look like an empty register. */
export function useEsiti(istanza = "") {
  const [esiti, setEsiti] = useState([]);
  const [caricamento, setCaricamento] = useState(true);
  const [errore, setErrore] = useState(null);
  const [stato, setStato] = useState("tutti");
  const [ricerca, setRicerca] = useState("");
  const [inSync, setInSync] = useState(false);
  const [esitoSync, setEsitoSync] = useState(null);
  const [anomalie, setAnomalie] = useState([]);
  const [erroreAnomalie, setErroreAnomalie] = useState(null);

  const ricarica = useCallback(async () => {
    setCaricamento(true);
    setErrore(null);
    try {
      setEsiti(await leggiEsiti(istanza));
    } catch (e) {
      setErrore(e.message || "errore sconosciuto");
    } finally {
      setCaricamento(false);
    }
  }, [istanza]);

  /** Kept apart from the list: a failed check must not hide the register,
   *  and must not pass for "no anomalies" either. */
  const controlla = useCallback(async () => {
    try {
      setAnomalie(await anomalieEsiti());
      setErroreAnomalie(null);
    } catch (e) {
      setErroreAnomalie(e.message || "errore sconosciuto");
    }
  }, []);

  useEffect(() => {
    ricarica();
    controlla();
  }, [ricarica, controlla]);

  const sincronizza = useCallback(async () => {
    setInSync(true);
    setEsitoSync(null);
    try {
      const r = await sincronizzaEsiti();
      if (Array.isArray(r.esiti)) setEsiti(r.esiti);
      controlla();
      setEsitoSync({ cambiati: r.cambiati || [], problemi: r.problemi || [], errore: null });
    } catch (e) {
      setEsitoSync({ cambiati: [], problemi: [], errore: e.message || "errore sconosciuto" });
    } finally {
      setInSync(false);
    }
  }, [controlla]);

  const conteggi = useMemo(() => {
    const c = { tutti: esiti.length };
    STATI.forEach((s) => { c[s] = esiti.filter((e) => e.stato === s).length; });
    return c;
  }, [esiti]);

  const visibili = useMemo(() => {
    const q = norm(ricerca).trim();
    return esiti.filter((e) => {
      if (stato !== "tutti" && e.stato !== stato) return false;
      if (!q) return true;
      return [
        e.strumento, e.sintesi, e.a_cosa_serve, e.problema, e.comando,
        ...(e.dove || []), ...(e.nodi || []), ...(e.funzionalita || []),
      ].some((t) => norm(t).includes(q));
    });
  }, [esiti, stato, ricerca]);

  const perCategoria = useMemo(() => raggruppa(visibili), [visibili]);

  return {
    esiti, visibili, perCategoria, conteggi, caricamento, errore, ricarica,
    stato, setStato, ricerca, setRicerca, inSync, esitoSync, sincronizza,
    anomalie, erroreAnomalie,
  };
}
