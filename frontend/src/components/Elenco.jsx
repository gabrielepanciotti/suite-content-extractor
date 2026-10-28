import { Badge, Button } from "@suite/design-system";
import { BadgeIstanza } from "./SceltaIstanza";

// Il tono di ogni etichetta. `da_vedere` resta neutro: e' l'unico stato che
// chiede un'azione, e colorarlo lo farebbe leggere come un esito.
const TONO = {
  da_vedere: undefined,
  integrato: "success",
  parziale: "warning",
  scartato: "danger",
  fallito: "danger",
};

const PARERE = {
  si: ["success", "consigliato"],
  no: ["danger", "sconsigliato"],
  misto: ["warning", "consigli misti"],
};

/** Il parere del giudizio su un contenuto, come tag. */
export function Consigliato({ valore }) {
  const p = PARERE[valore];
  return p ? <Badge state={p[0]}>{p[1]}</Badge> : null;
}

/** Cosa si vede nell'elenco, nell'ordine in cui lo si scorre.
 *
 *  Una funzione sola, usata anche dal «Prossimo contenuto»: se le frecce e il
 *  bottone ordinassero in due modi diversi, «prossimo» porterebbe altrove. */
export function visibiliOrdinati(schede, solo, ordine, correnteId) {
  const filtrate = solo === "da_decidere"
    ? schede.filter((s) => s.stato === "da_vedere" || s.source_id === correnteId)
    : schede;
  // «Efficacia»: la stima del giudice sull'effetto nei sistemi, la migliore
  // prima, quelle senza stima in fondo. «Recenti»: per data di arrivo.
  return [...filtrate].sort((a, b) =>
    ordine === "efficacia"
      ? (b.impatto || 0) - (a.impatto || 0) || b.caricato.localeCompare(a.caricato)
      : b.caricato.localeCompare(a.caricato),
  );
}

/** Colonna di sinistra: tutti i contenuti, per spostarsi dall'uno all'altro.
 *
 *  Dice a colpo d'occhio cosa richiede attenzione: «manca contenuto» (il post
 *  promette qualcosa che arriva solo con un'azione tua) e «rielaborazione»
 *  (una fonte aggiunta e' in lettura adesso). Le frecce scorrono la lista
 *  com'e' filtrata, cosi' si va avanti senza tornare a cercare nell'elenco.
 */
export default function Elenco({
  schede,
  correnteId,
  onApri,
  solo,
  onSolo,
  ordine = "efficacia",
  onOrdine = () => {},
  mostraIstanza = false,
}) {
  const visibili = visibiliOrdinati(schede, solo, ordine, correnteId);
  const pos = visibili.findIndex((s) => s.source_id === correnteId);
  const vai = (d) => {
    const dest = visibili[pos + d];
    if (dest) onApri(dest.source_id);
  };

  return (
    <nav aria-label="Contenuti" className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-border p-3">
        <Button
          size="sm"
          variant="secondary"
          aria-label="Contenuto precedente"
          disabled={pos <= 0}
          onClick={() => vai(-1)}
        >
          ←
        </Button>
        <Button
          size="sm"
          variant="secondary"
          aria-label="Contenuto successivo"
          disabled={pos < 0 || pos >= visibili.length - 1}
          onClick={() => vai(1)}
        >
          →
        </Button>
        <span className="flex-1 text-center text-xs text-muted tabular-nums">
          {pos >= 0 ? `${pos + 1} di ${visibili.length}` : `${visibili.length}`}
        </span>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => onSolo(solo === "da_decidere" ? "tutti" : "da_decidere")}
        >
          {solo === "da_decidere" ? "Mostra tutti" : "Solo da decidere"}
        </Button>
      </div>
      <div className="flex items-center gap-2 border-b border-border px-3 py-2 text-xs text-muted">
        Ordina per
        {[["efficacia", "efficacia"], ["recenti", "più recenti"]].map(([v, et]) => (
          <Button key={v} variant="ghost" size="sm" type="button" aria-pressed={ordine === v}
            onClick={() => onOrdine(v)} className={`rounded-button border px-2 py-0.5 ${ordine === v ? "border-info bg-info/15 text-text font-medium" : "border-border text-muted hover:text-text"}`}>
            {et}
          </Button>
        ))}
      </div>
      {visibili.length === 0 ? (
        <p className="p-4 text-sm text-muted">Niente da decidere.</p>
      ) : (
        <ul className="flex-1 divide-y divide-border overflow-y-auto">
          {visibili.map((s) => {
            const attivo = s.source_id === correnteId;
            return (
              <li key={s.source_id}>
                <Button
                  variant="ghost"
                  onClick={() => onApri(s.source_id)}
                  aria-current={attivo ? "true" : undefined}
                  className={`block h-auto w-full justify-start whitespace-normal rounded-none px-3 py-2 text-left font-normal text-text transition-colors hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-info ${
                    attivo ? "bg-surface-2" : ""
                  }`}
                >
                  <span className="block text-sm font-medium">
                    {s.titolo || s.source_id}
                  </span>
                  <span className="mt-1 flex flex-wrap items-center gap-1">
                    {mostraIstanza && <BadgeIstanza id={s.instance_id} />}
                    <Badge state={TONO[s.stato]}>{s.stato_etichetta}</Badge>
                    {s.in_rielaborazione && (
                      <Badge state="warning">rielaborazione…</Badge>
                    )}
                    <Consigliato valore={s.consigliato} />
                    {s.impatto && (
                      <span className="text-xs text-muted" title="Efficacia stimata nei tuoi sistemi, da 1 a 5">
                        ★ {s.impatto}/5
                      </span>
                    )}
                    {s.materiale_aggiunto && <Badge>materiale aggiunto</Badge>}
                    {s.manca_allegato && (
                      <Badge state="danger">manca contenuto</Badge>
                    )}
                    <span className="text-xs text-muted">{s.quante_tip} tip</span>
                  </span>
                </Button>
              </li>
            );
          })}
        </ul>
      )}
    </nav>
  );
}
