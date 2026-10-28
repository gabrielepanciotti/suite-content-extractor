import { useState } from "react";
import { Button, Input } from "@suite/design-system";
import { useRepos } from "../hooks/useRepos";

const chip =
  "inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs transition-colors " +
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-info";

/** Pick the projects an issue goes to, from the ones that really exist.
 *
 *  A free text field pre-filled with the judgement let a sentence through to
 *  `gh --repo`; choosing from a list makes that impossible by construction.
 */
export default function SceltaProgetti({ scelti, onCambia }) {
  const { elenco, errore } = useRepos();
  const [cerca, setCerca] = useState("");

  const commuta = (nome) =>
    onCambia(scelti.includes(nome) ? scelti.filter((n) => n !== nome) : [...scelti, nome]);

  const filtro = cerca.trim().toLowerCase();
  const proposti = elenco
    .filter((r) => !scelti.includes(r.nome))
    .filter((r) => !filtro || r.nome.toLowerCase().includes(filtro))
    ;

  return (
    <div className="grid gap-2">
      <p className="text-xs font-medium text-muted">In quali progetti aprire l'issue</p>
      {scelti.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {scelti.map((nome) => (
            <Button
              key={nome}
              type="button"
              aria-pressed="true"
              aria-label={`togli ${nome}`}
              onClick={() => commuta(nome)}
              className={`${chip} border-border bg-surface text-text hover:bg-surface-2`}
            >
              {nome} <span aria-hidden>×</span>
            </Button>
          ))}
        </div>
      )}
      <Input
        aria-label="cerca progetto"
        placeholder="Cerca un progetto"
        value={cerca}
        onChange={(e) => setCerca(e.target.value)}
      />
      <div className="flex max-h-44 flex-wrap gap-2 overflow-y-auto">
        {proposti.map((r) =>
          r.esiste === false ? (
            // A repo GitHub does not know: an adoption aimed there would open
            // no issue, so it cannot be picked, and the reason stays visible.
            <Button
              key={r.nome}
              type="button"
              disabled
              aria-disabled="true"
              title={r.motivo || "non esiste su GitHub"}
              className={`${chip} cursor-not-allowed border-border text-muted opacity-60`}
            >
              {r.nome} <span className="text-danger">non esiste su GitHub</span>
            </Button>
          ) : (
            <Button
              key={r.nome}
              type="button"
              aria-pressed="false"
              onClick={() => {
                commuta(r.nome);
                setCerca("");
              }}
              className={`${chip} border-border text-muted hover:bg-surface-2 hover:text-text`}
            >
              + {r.nome}
            </Button>
          ),
        )}
      </div>
      {errore && (
        <p className="text-xs text-danger">Non riesco a leggere i progetti: {errore}</p>
      )}
    </div>
  );
}
