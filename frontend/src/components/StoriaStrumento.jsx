import { Badge } from "@suite/design-system";
import { ETICHETTA_COSTO } from "../lib/categorie";
import { ETICHETTA_STATO, TONO_STATO, etichettaIssue } from "../lib/stati";
import Collegamento from "./Collegamento";
import ContenutoEsito, { cosaDiceLaFonte } from "./ContenutoEsito";

/** One step of the story: a dot on the line, a label, its content. */
function Tappa({ titolo, children }) {
  return (
    <li className="relative pl-5">
      <span
        aria-hidden
        className="absolute left-[-6px] top-1 h-2.5 w-2.5 rounded-full border-2 border-info bg-surface"
      />
      <h5 className="text-xs font-semibold uppercase tracking-wide text-info">
        {titolo}
      </h5>
      <div className="mt-1 text-sm">{children}</div>
    </li>
  );
}

/** «Storia»: where the tool came from, what the source proposed, how we built
 *  it, where it stands today. The order is the story's, so it is a list. */
export default function StoriaStrumento({ esito: e }) {
  const idea = e.idea_originale || cosaDiceLaFonte(e.contenuto);
  const data = e.aggiornato ? new Date(e.aggiornato) : null;
  return (
    <div className="min-w-0">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-muted">
        Storia
      </h4>
      <ol className="mt-2 grid gap-4 border-l-2 border-border">
        <Tappa titolo="Fonte">
          <ContenutoEsito contenuto={e.contenuto} />
        </Tappa>
        {idea && (
          <Tappa titolo="Idea originale">
            <p
              data-testid="idea"
              className="line-clamp-4 whitespace-pre-line leading-relaxed"
            >
              {idea}
            </p>
          </Tappa>
        )}
        <Tappa titolo="Come l'abbiamo fatto">
          {e.implementazione && (
            <p className="leading-relaxed">{e.implementazione}</p>
          )}
          {e.stato === "unito" && e.unito_in && (
            <p className="mt-1 text-xs">
              {/^https?:/.test(e.unito_in) ? (
                <Collegamento href={e.unito_in}>
                  unito in {etichettaIssue(e.unito_in)}
                </Collegamento>
              ) : (
                <span>unito in {e.unito_in}</span>
              )}
            </p>
          )}
          <p className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs">
            {e.issue?.map((u) => (
              <Collegamento key={u} href={u}>
                {etichettaIssue(u)}
              </Collegamento>
            ))}
            {e.commit?.map((c) => (
              <span key={c} className="font-mono text-muted">
                {c}
              </span>
            ))}
          </p>
          {e.dove?.length > 0 && (
            <ul className="mt-1 list-disc pl-5 text-xs text-muted">
              {e.dove.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          )}
        </Tappa>
        <Tappa titolo="Oggi">
          <p className="flex flex-wrap items-center gap-2">
            <Badge state={TONO_STATO[e.stato]}>
              {ETICHETTA_STATO[e.stato] || e.stato}
            </Badge>
            {e.costo && (
              <span className="rounded-md border border-border px-1.5 text-xs text-muted">
                {ETICHETTA_COSTO[e.costo] || e.costo}
              </span>
            )}
            {e.issue_stato && (
              <span className="text-xs text-muted">
                issue {e.issue_stato === "closed" ? "chiusa" : "aperta"}
              </span>
            )}
            {data && !Number.isNaN(data.getTime()) && (
              <span className="text-xs text-muted">
                aggiornato {e.aggiornato}
              </span>
            )}
          </p>
          {e.nodi?.length > 0 && (
            <p
              className="mt-2 flex flex-wrap gap-1"
              aria-label="nodi che lo usano"
            >
              {e.nodi.map((n) => (
                <span
                  key={n}
                  className="rounded-md border border-border px-1.5 text-xs text-muted"
                >
                  {n}
                </span>
              ))}
            </p>
          )}
        </Tappa>
      </ol>
    </div>
  );
}
