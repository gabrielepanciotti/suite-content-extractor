import { useState } from "react";
import { Button } from "@suite/design-system";
import { letture } from "../lib/api";

/** Lo storico delle letture di un contenuto: cosa e' successo, quando, e con
 *  quale fonte aggiunta (link, file, testo incollato) e' stato rielaborato.
 *
 *  Chiuso di default e caricato solo all'apertura: serve a chi si chiede
 *  perche' una scheda ha quelle tip, non a chi sta decidendo. */
export default function Storico({ sourceId }) {
  const [righe, setRighe] = useState(null);
  const [errore, setErrore] = useState(null);

  const apri = () => {
    letture(sourceId).then(setRighe).catch((e) => setErrore(e.message));
  };

  if (righe === null) {
    return (
      <div className="mt-4 text-sm">
        <Button variant="link" size="sm" className="text-muted" onClick={apri}>
          Storico delle letture
        </Button>
        {errore && <span className="ml-2 text-danger">{errore}</span>}
      </div>
    );
  }
  return (
    <section className="mt-4 text-sm">
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted">
        Storico delle letture
      </h3>
      {righe.length === 0 ? (
        <p className="mt-1 text-muted">Nessuna lettura registrata.</p>
      ) : (
        <ul className="mt-1 grid gap-1">
          {righe.map((r, i) => (
            <li key={i} className="text-muted">
              <span className="tabular-nums">
                {r.quando ? new Date(r.quando).toLocaleString("it-IT") : "data non registrata"}
              </span>{" "}
              — {r.fonte ? `con ${r.fonte}` : i === 0 ? "prima lettura" : "riletto"}:{" "}
              {r.esito}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
