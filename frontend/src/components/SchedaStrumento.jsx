import Comando from "./Comando";
import { Apribile } from "./ContenutoEsito";
import Guida from "./Guida";

function Titolo({ children }) {
  return (
    <h4 className="mt-4 text-xs font-semibold uppercase tracking-wide text-muted first:mt-0">
      {children}
    </h4>
  );
}

/** «Cosa fa»: what the tool is for, the problem, what it does, how to use it,
 *  told to someone who never saw it. The issue's guide follows, folded when
 *  the card already says how to use it, open when it is all there is. */
export default function SchedaStrumento({ esito: e }) {
  const haScheda = Boolean(e.a_cosa_serve || e.passi?.length);
  return (
    <div className="min-w-0">
      <Titolo>A cosa serve</Titolo>
      <p className="mt-1 text-base font-medium leading-relaxed">
        {e.a_cosa_serve || e.sintesi || "Scheda non ancora scritta nell'issue."}
      </p>
      {e.problema && (
        <>
          <Titolo>Problema che risolve</Titolo>
          <p className="mt-1 text-sm leading-relaxed">{e.problema}</p>
        </>
      )}
      {e.funzionalita?.length > 0 && (
        <>
          <Titolo>Funzionalità</Titolo>
          <ul className="mt-1 list-disc pl-5 text-sm leading-relaxed">
            {e.funzionalita.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </>
      )}
      {(e.passi?.length > 0 || e.comando || e.come_si_usa) && (
        <>
          <Titolo>Come si usa</Titolo>
          {e.passi?.length > 0 ? (
            <ol className="mt-1 list-decimal pl-5 text-sm leading-relaxed">
              {e.passi.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ol>
          ) : (
            e.come_si_usa && (
              <p className="mt-1 whitespace-pre-line text-sm">
                {e.come_si_usa}
              </p>
            )
          )}
          {e.comando && <Comando testo={e.comando} />}
        </>
      )}
      {e.guida ? (
        <Apribile titolo="Guida completa (dall'issue)" iniziale={!haScheda}>
          <Guida testo={e.guida} />
        </Apribile>
      ) : (
        <p className="mt-3 text-xs text-muted">Guida non ancora scritta.</p>
      )}
    </div>
  );
}
