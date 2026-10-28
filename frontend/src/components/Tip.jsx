import { Badge } from "@suite/design-system";

const TONO_STATO = { adopted: "success", rejected: "danger", failed: "danger" };

// The queue stores these values in English because code reads them; a person
// reads the page, and the page is in Italian.
const RACCOMANDAZIONE = {
  adopt: "consigliata",
  skip: "sconsigliata",
  unknown: "non giudicata",
};
const STATO = {
  adopted: "approvata",
  rejected: "declinata",
  failed: "fallita",
  pending: "da decidere",
};

/** Una tip, con tutto cio' su cui si decide — e niente di piu'.
 *
 *  Non decide: i bottoni arrivano da fuori come `children`. Uno strumento si
 *  decide a cascata e un utilizzo no, quindi la carta non puo' sapere da sola
 *  quale azione le appartiene; sapendolo, avrebbe due comportamenti e nessun
 *  modo di provarli separatamente.
 */
export default function Tip({ tip, principale = false, children = null }) {
  const decisa = tip.stato !== "pending";
  return (
    <article
      className={`rounded-lg border p-4 ${
        principale ? "border-border bg-surface-2" : "border-border"
      }`}
    >
      <header className="flex flex-wrap items-start gap-2">
        <h3
          className={`flex-1 ${principale ? "text-base font-semibold" : "font-medium"}`}
        >
          {tip.titolo}
        </h3>
        <Badge state={tip.raccomandazione === "adopt" ? "success" : undefined}>
          {RACCOMANDAZIONE[tip.raccomandazione] ?? tip.raccomandazione}
        </Badge>
        {decisa && (
          <Badge state={TONO_STATO[tip.stato]}>
            {STATO[tip.stato] ?? tip.stato}
          </Badge>
        )}
      </header>

      {/* Accanto alla raccomandazione, non in fondo: un giudizio dato senza
          aver visto il video vale meno di uno completo, e la differenza conta
          NEL MOMENTO in cui si decide. */}
      {(tip.degradato || tip.nota_giudizio) && (
        <p className="mt-2 text-xs text-warning">
          {tip.degradato || tip.nota_giudizio}
        </p>
      )}

      {/* Il motivo sta sotto il verdetto, non in fondo: e' cio' su cui si
          decide, e un verdetto senza motivo chiede fiducia invece di darne
          ragione. Distinto da nota_giudizio sopra, che dice un'altra cosa —
          che il giudizio e' stato dato con un contesto incompleto. */}
      {tip.motivo_verdetto && (
        <p className="mt-2 text-sm text-muted">{tip.motivo_verdetto}</p>
      )}

      {/* Una tip fallita ha il corpo vuoto: senza questa riga la carta mostra
          "fallita" e nient'altro, cioe' esattamente quanto se ne sapeva prima
          di aprirla. Il motivo e' l'unica cosa che dice cosa farci. */}
      {tip.stato === "failed" && tip.motivo_fallimento && (
        <p className="mt-2 text-sm text-warning">
          Non estratta: {tip.motivo_fallimento}.
        </p>
      )}

      <p className="mt-2 text-sm">{tip.corpo}</p>

      {/* Dove la pratica verrebbe scritta: e' meta' della decisione, perche'
          una tip che non ha un posto dove andare non si adotta, si annota. */}
      {tip.repo && (
        <p className="mt-2 text-xs text-muted">
          <span className="uppercase tracking-wide">Andrebbe in</span>{" "}
          <code>{tip.repo}</code>
        </p>
      )}

      {/* Il marcatore sta in un elemento suo: fuso nello stesso nodo di testo
          renderebbe ogni pro/contro irraggiungibile da solo, da un test o da
          uno screen reader che legge "piu' e' documentato". */}
      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <ul className="text-sm">
          {tip.pros.map((p) => (
            <li key={p} className="flex gap-2">
              <span aria-hidden>+</span>
              <span>{p}</span>
            </li>
          ))}
        </ul>
        <ul className="text-sm text-muted">
          {tip.cons.map((c) => (
            <li key={c} className="flex gap-2">
              <span aria-hidden>−</span>
              <span>{c}</span>
            </li>
          ))}
        </ul>
      </div>

      {tip.approfondimento && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-muted">
            Approfondimento
          </summary>
          <p className="mt-2 whitespace-pre-wrap">{tip.approfondimento}</p>
        </details>
      )}

      {children}
    </article>
  );
}
