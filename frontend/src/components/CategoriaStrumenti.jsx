import { ETICHETTA_STATO, PUNTO_STATO, STATI } from "../lib/stati";
import EsitoCard from "./EsitoCard";

/** One category: a header with how many tools sit in each state, then the
 *  tools as compact rows. */
export default function CategoriaStrumenti({
  gruppo,
  aperti,
  alterna,
  mostraIstanza,
}) {
  const { key, nome, descrizione, esiti } = gruppo;
  return (
    <section
      id={`categoria-${key || "senza"}`}
      aria-labelledby={`categoria-${key || "senza"}-titolo`}
      className="mt-6 scroll-mt-4"
    >
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-border pb-1.5">
        <h2
          id={`categoria-${key || "senza"}-titolo`}
          className="text-base font-semibold"
        >
          {nome}
        </h2>
        <span className="text-xs text-muted">{descrizione}</span>
        <span className="flex flex-wrap gap-3 text-xs text-muted sm:ml-auto">
          {STATI.filter((s) => esiti.some((e) => e.stato === s)).map((s) => (
            <span key={s} className="inline-flex items-center gap-1">
              <span
                aria-hidden
                className={`h-1.5 w-1.5 rounded-full ${PUNTO_STATO[s]}`}
              />
              <span className="tabular-nums">
                {esiti.filter((e) => e.stato === s).length}
              </span>{" "}
              {ETICHETTA_STATO[s]}
            </span>
          ))}
        </span>
      </header>
      <div>
        {esiti.map((e) => (
          <EsitoCard
            key={e.id}
            esito={e}
            aperto={aperti.has(e.id)}
            onToggle={() => alterna(e.id)}
            mostraIstanza={mostraIstanza}
          />
        ))}
      </div>
    </section>
  );
}
