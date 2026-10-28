import { useCallback, useEffect, useRef, useState } from "react";

const PREFISSO = "bozza:";

const leggi = (chiave) => {
  try {
    const grezzo = window.localStorage.getItem(PREFISSO + chiave);
    return grezzo ? JSON.parse(grezzo) : null;
  } catch {
    return null;
  }
};

const scrivi = (chiave, valore) => {
  try {
    window.localStorage.setItem(PREFISSO + chiave, JSON.stringify(valore));
  } catch {
    // Storage pieno o bloccato: la bozza non si salva, il modulo funziona lo stesso.
  }
};

const cancella = (chiave) => {
  try {
    window.localStorage.removeItem(PREFISSO + chiave);
  } catch {
    // niente da fare: vedi sopra
  }
};

/** Cio' che scrivi non si perde mai.
 *
 *  Stato di un modulo salvato nel browser a ogni modifica e ripreso alla
 *  riapertura: un ricaricamento della pagina, un redeploy o una chiusura per
 *  sbaglio non cancellano una nota scritta a meta'. Regola base di ogni
 *  progetto: il testo di una persona e' piu' prezioso del tempo che ci mette
 *  a riscriverlo.
 *
 *  Ritorna `[valori, imposta, svuota]`: `imposta` fonde un pezzo di stato,
 *  `svuota` cancella la bozza (da chiamare quando l'invio e' riuscito).
 */
export function useBozza(chiave, iniziale) {
  const [valori, setValori] = useState(() => ({ ...iniziale, ...(leggi(chiave) ?? {}) }));
  const svuotata = useRef(false);

  useEffect(() => {
    if (svuotata.current) return;
    scrivi(chiave, valori);
  }, [chiave, valori]);

  const imposta = useCallback((pezzo) => {
    svuotata.current = false;
    setValori((v) => ({ ...v, ...pezzo }));
  }, []);

  const svuota = useCallback(() => {
    svuotata.current = true;
    cancella(chiave);
    setValori({ ...iniziale });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chiave]);

  return [valori, imposta, svuota];
}
