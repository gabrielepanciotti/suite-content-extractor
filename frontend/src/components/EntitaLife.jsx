import { useState } from "react";
import { Button } from "@suite/design-system";

export const ENTITA = ["Life work", "Life personal", "Life"];

/** L'entita' Life da cui e' arrivato il contenuto, correggibile a mano.
 *
 *  Preselezionata da dove e' stato mandato (il gruppo, il bot); qui si cambia
 *  se la tip riguarda un'altra entita' o tutta Life. */
export default function EntitaLife({ valore, onCambia }) {
  const [errore, setErrore] = useState(null);
  const scegli = async (v) => {
    setErrore(null);
    try {
      await onCambia(v);
    } catch (e) {
      setErrore(e.message || "non salvato");
    }
  };
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      {ENTITA.map((v) => (
        <Button key={v} variant="ghost" size="sm" type="button" aria-pressed={valore === v}
          onClick={() => scegli(v)} className={`inline-flex items-center rounded-full border px-3 py-1 transition-colors ${valore === v ? "border-border bg-surface font-medium text-text" : "border-border bg-surface text-muted hover:bg-surface-2 hover:text-text"}`}>
          {v}
        </Button>
      ))}
      {!valore && <span className="text-warning">non indicata</span>}
      {errore && <span className="text-danger">{errore}</span>}
    </div>
  );
}
