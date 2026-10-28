import { Badge, Button } from "@suite/design-system";
import { ETICHETTA_COSTO } from "../lib/categorie";
import { ETICHETTA_STATO, PUNTO_STATO, TONO_STATO } from "../lib/stati";
import { BadgeIstanza } from "./SceltaIstanza";
import SchedaStrumento from "./SchedaStrumento";
import StoriaStrumento from "./StoriaStrumento";

export { ETICHETTA_STATO, etichettaIssue } from "../lib/stati";

/** One tool: a compact row that is the toggle, and when open its card in two
 *  columns, «what it does» (3/5) and «its story» (2/5), stacked on mobile. */
export default function EsitoCard({
  esito: e,
  aperto = false,
  onToggle = () => {},
  mostraIstanza = false,
}) {
  const idDettaglio = `esito-${e.id}`;
  return (
    <article
      id={idDettaglio}
      className="border-b border-border [overflow-wrap:anywhere] last:border-b-0"
    >
      <Button
        variant="ghost"
        aria-expanded={aperto}
        aria-controls={`${idDettaglio}-dettaglio`}
        onClick={onToggle}
        className="grid w-full grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-0.5 rounded-lg px-2 py-2.5 text-left transition-colors hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-info md:grid-cols-[auto_minmax(10rem,15rem)_minmax(0,1fr)_auto]"
      >
        <span
          aria-hidden
          className={`h-2 w-2 rounded-full ${PUNTO_STATO[e.stato] || "bg-muted"}`}
        />
        <h3 className="text-sm font-semibold">{e.strumento}</h3>
        <span className="col-start-2 row-start-2 min-w-0 truncate text-sm text-muted md:col-start-3 md:row-start-1">
          {e.a_cosa_serve || e.sintesi}
        </span>
        <span className="col-start-3 row-start-1 flex items-center gap-1.5 md:col-start-4">
          {mostraIstanza && <BadgeIstanza id={e.instance_id} />}
          {e.costo && (
            <span className="hidden rounded-md border border-border px-1.5 text-xs text-muted sm:inline">
              {ETICHETTA_COSTO[e.costo] || e.costo}
            </span>
          )}
          <Badge state={TONO_STATO[e.stato]}>
            {ETICHETTA_STATO[e.stato] || e.stato}
          </Badge>
          <span
            aria-hidden
            className={`text-muted transition-transform ${aperto ? "rotate-90" : ""}`}
          >
            ▸
          </span>
        </span>
      </Button>
      {aperto && (
        <div
          id={`${idDettaglio}-dettaglio`}
          className="grid gap-6 px-2 pb-5 pt-2 md:grid-cols-5 md:pl-7"
        >
          <div className="min-w-0 md:col-span-3">
            <SchedaStrumento esito={e} />
          </div>
          <div className="min-w-0 md:col-span-2">
            <StoriaStrumento esito={e} />
          </div>
        </div>
      )}
    </article>
  );
}
