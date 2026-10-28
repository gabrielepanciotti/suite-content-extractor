import { useState } from "react";
import { Badge, Button } from "@suite/design-system";
import Tip from "./Tip";
import Decisione from "./Decisione";

/** Uno strumento e i modi di usarlo, nell'ordine in cui si decidono.
 *
 *  Prima «lo voglio?», poi «per fare cosa?». Rispondere alla prima chiude
 *  anche la seconda — e la pagina lo dice sul bottone, non dopo il clic.
 */
export default function Gruppo({
  gruppo,
  onDecidiStrumento,
  onDecidiTip,
  inCorso,
  soloLettura = false,
  entita = null,
}) {
  const aperti = gruppo.utilizzi.filter((u) => u.stato === "pending");
  // Approvato lo strumento e decisi i suoi usi, la card si riduce al titolo:
  // non c'e' piu' niente da decidere, e il resto resta a un clic.
  const deciso =
    gruppo.tip && gruppo.tip.stato !== "pending" && aperti.length === 0;
  const [espansa, setEspansa] = useState(false);
  if (deciso && !espansa) {
    return (
      <section className="rounded-xl border border-border p-3">
        <Button
          variant="ghost"
          onClick={() => setEspansa(true)}
          className="flex w-full flex-wrap items-center gap-2 text-left"
        >
          <Badge state={gruppo.tip.stato === "adopted" ? "success" : "danger"}>
            {gruppo.tip.stato === "adopted" ? "approvato" : "declinato"}
          </Badge>
          <h3 className="font-semibold">{gruppo.strumento}</h3>
          <span className="ml-auto text-xs text-muted">mostra</span>
        </Button>
      </section>
    );
  }
  return (
    <section className="grid gap-3 rounded-xl border border-border p-3">
      <header className="flex flex-wrap items-center gap-2">
        <Badge>strumento</Badge>
        <h3 className="font-semibold">{gruppo.strumento}</h3>
        {deciso && (
          <Button
            variant="link"
            size="sm"
            onClick={() => setEspansa(false)}
            className="ml-auto text-xs text-muted underline"
          >
            comprimi
          </Button>
        )}
      </header>

      {gruppo.tip ? (
        <Tip tip={gruppo.tip} principale>
          {gruppo.tip.stato === "pending" && !soloLettura && (
            <Decisione
              entita={entita}
              tip={gruppo.tip}
              cascata={aperti.length > 0}
              inCorso={inCorso}
              onDecidi={(corpo) => onDecidiStrumento(gruppo.tip.id, corpo)}
            />
          )}
        </Tip>
      ) : (
        // Un gruppo senza la sua tip-strumento non e' un errore: il contenuto
        // parlava di usi di qualcosa che non ha presentato. Dirlo evita che
        // manchi un bottone senza spiegazione.
        <p className="text-sm text-muted">
          Il contenuto non presenta lo strumento in sé, solo modi di usarlo:
          qui si decide un utilizzo alla volta.
        </p>
      )}

      {gruppo.utilizzi.length > 0 && (
        <>
          <h4 className="text-xs font-medium uppercase tracking-wide text-muted">
            Dove e come si può integrare
          </h4>
          <div className="grid gap-3 sm:pl-4">
            {gruppo.utilizzi.map((u) => (
              <Tip key={u.id} tip={u}>
                {u.stato === "pending" && !soloLettura && (
                  <Decisione
                    entita={entita}
                    tip={u}
                    inCorso={inCorso}
                    onDecidi={(corpo) => onDecidiTip(u.id, corpo)}
                  />
                )}
              </Tip>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
