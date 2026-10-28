import { useState } from "react";
import { useBozza } from "../hooks/useBozza";
import { Button, Input, Textarea } from "@suite/design-system";

/** Il materiale che il post consegnava solo a mano, riportato qui dentro.
 *
 *  Un campo solo alla volta, non due: link e file sono due materiali diversi
 *  e il backend ne accetta uno per volta — chi ne ha due li manda due volte,
 *  e le tip si sommano sulla stessa scheda. Offrirli insieme prometterebbe
 *  una cosa che il server rifiuta con un 422.
 *
 *  Non decide niente e non sa dove finisce: riceve `onInvia` e lo chiama.
 */
export default function Materiale({ onInvia, lavoro = null, inCorso = false, sourceId = null }) {
  const [bozza, imposta, svuota] = useBozza(`materiale:${sourceId ?? "x"}`, { link: "", testo: "" });
  const link = bozza.link;
  const testo = bozza.testo ?? "";
  const setLink = (v) => imposta({ link: v });
  const setTesto = (v) => imposta({ testo: v });
  const [file, setFile] = useState(null);
  const [errore, setErrore] = useState(null);
  const [altro, setAltro] = useState(false);

  // Una sola fonte per volta: link, file o testo incollato.
  const pronto =
    [Boolean(link.trim()), Boolean(file), Boolean(testo.trim())].filter(Boolean)
      .length === 1;

  const invia = async () => {
    setErrore(null);
    try {
      // Il testo incollato viaggia come file .txt: un nome nuovo ogni volta,
      // cosi' una seconda aggiunta non sovrascrive la prima.
      const daTesto = testo.trim()
        ? new File([testo], `testo-incollato-${Date.now()}.txt`, { type: "text/plain" })
        : null;
      await onInvia({ link: link.trim() || null, file: file || daTesto });
      svuota();
      setFile(null);
    } catch (e) {
      setErrore(e.message || "non è riuscito");
    }
  };

  // Mentre gira non si ricarica: un secondo invio partirebbe sullo stesso
  // contenuto mentre il primo sta ancora scrivendo nella stessa coda.
  if (lavoro?.stato === "in_corso") {
    return (
      <p className="mt-3 text-sm text-muted">
        Sto rileggendo il contenuto con quello che hai caricato. Ci vuole
        qualche minuto: puoi andare avanti, la scheda si aggiorna da sola.
      </p>
    );
  }

  // Consegnato e riletto: il modulo non si ripropone da solo. Chiederlo di
  // nuovo faceva credere che il caricamento fosse andato perso.
  if (lavoro?.stato === "finita" && !altro) {
    return (
      <div className="mt-3 grid gap-1 text-sm">
        <p className="text-muted">
          Materiale caricato
          {lavoro.materiale ? `: ${lavoro.materiale.slice(0, 70)}` : ""}.{" "}
          {lavoro.esito}
        </p>
        <div>
          <Button variant="link" size="sm" className="text-muted" onClick={() => setAltro(true)}>
            Aggiungi altro materiale
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-3 grid gap-2">
      {lavoro?.stato === "fallita" && (
        <p className="text-sm text-danger">
          L&apos;ultimo tentativo non è andato a buon fine: {lavoro.esito}
        </p>
      )}
      {lavoro?.stato === "finita" && (
        <p className="text-sm text-muted">Ultima rilettura: {lavoro.esito}</p>
      )}

      <label className="grid gap-1 text-sm">
        <span className="text-muted">Il link che hai ricevuto</span>
        <Input
          type="url"
          value={link}
          onChange={(e) => setLink(e.target.value)}
          placeholder="https://…"
          className="rounded-md border border-border bg-surface px-3 py-2"
        />
      </label>

      <label className="grid gap-1 text-sm">
        <span className="text-muted">…oppure il file</span>
        <Input
          type="file"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="text-sm"
        />
      </label>

      <label className="grid gap-1 text-sm">
        <span className="text-muted">…oppure incolla il testo (es. quello sbloccato col commento)</span>
        <Textarea
          rows={4}
          value={testo}
          onChange={(e) => setTesto(e.target.value)}
          className="rounded-md border border-border bg-surface px-3 py-2"
        />
      </label>

      {errore && <p className="text-sm text-danger">{errore}</p>}

      <div>
        <Button onClick={invia} disabled={!pronto || inCorso}>
          Aggiungi e rielabora
        </Button>
      </div>
    </div>
  );
}
