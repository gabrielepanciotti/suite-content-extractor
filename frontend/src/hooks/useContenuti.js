import { useCallback, useEffect, useState } from "react";
import { elenco } from "../lib/api";

/** Loads the list of ingested contents, keeping load and error states apart:
 *  an empty list is a legitimate answer, a failure is not, and the UI must be
 *  able to tell them apart instead of showing the same blank page for both. */
export function useContenuti(istanza = "") {
  const [schede, setSchede] = useState([]);
  const [caricamento, setCaricamento] = useState(true);
  const [errore, setErrore] = useState(null);

  const ricarica = useCallback(async () => {
    setCaricamento(true);
    setErrore(null);
    try {
      setSchede(await elenco(istanza));
    } catch (e) {
      setErrore(e.message || "errore sconosciuto");
    } finally {
      setCaricamento(false);
    }
  }, [istanza]);

  useEffect(() => {
    ricarica();
  }, [ricarica]);

  return { schede, caricamento, errore, ricarica };
}
