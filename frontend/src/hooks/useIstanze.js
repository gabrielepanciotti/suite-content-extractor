import { useCallback, useEffect, useState } from "react";
import { istanze as leggiIstanze } from "../lib/api";

const CHIAVE = "content-extractor.istanza";

/** The Life instances this operator serves, and the one being looked at.
 *  "" means every instance (the «tutte» view). The choice survives a reload:
 *  whoever works on one instance should not be thrown back to all of them. */
export function useIstanze() {
  const [istanze, setIstanze] = useState([]);
  const [errore, setErrore] = useState(null);
  const [scelta, setSceltaStato] = useState(() => {
    try {
      return window.localStorage.getItem(CHIAVE) || "";
    } catch {
      return "";
    }
  });

  useEffect(() => {
    leggiIstanze()
      .then((lette) => {
        setIstanze(lette);
        // A remembered instance that is no longer registered would make every
        // read a 422: fall back to «tutte» instead of an empty page.
        if (scelta && !lette.some((i) => i.id === scelta)) setSceltaStato("");
      })
      .catch((e) => setErrore(e.message || "errore sconosciuto"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setScelta = useCallback((id) => {
    setSceltaStato(id);
    try {
      window.localStorage.setItem(CHIAVE, id);
    } catch {
      /* private mode: the choice just doesn't persist */
    }
  }, []);

  return { istanze, scelta, setScelta, errore };
}
