import { useState } from "react";
import { origine } from "../lib/etichette";
import { hrefSicuro } from "../lib/url";
import { Badge, Button } from "@suite/design-system";
import Gruppo from "./Gruppo";
import Tip from "./Tip";
import Decisione from "./Decisione";
import Materiale from "./Materiale";
import Storico from "./Storico";
import { Consigliato } from "./Elenco";

const restanti = (scheda) =>
  scheda.tip.filter((t) => t.stato === "pending").length;

/** Un contenuto per volta: gli strumenti con i loro utilizzi, poi le pratiche.
 *
 *  Il passaggio al contenuto successivo e' chiuso finche' resta qualcosa di
 *  indeciso. Non e' rigore per il gusto di esserlo: una tip saltata resta
 *  `pending` per sempre, e una coda dove il non-deciso e il non-ancora-visto
 *  hanno lo stesso aspetto smette di dire cosa manca.
 */
export default function Scheda({
  scheda,
  onDecidiStrumento,
  onDecidiTip,
  onDecidiPacchetto = null,
  onDecidiTutti = null,
  onCambiaEntita = null,
  onProssimo = null,
  inCorso = false,
  issueUrls = [],
  lavoro = null,
  onMateriale = null,
}) {
  const aperte = restanti(scheda);
  // Nessuno strumento a capo e piu' tip aperte: sono i capitoli di una cosa
  // sola (una skill spiegata in quattro parti). Si approva intera, una volta.
  const pacchetto =
    onDecidiPacchetto !== null &&
    aperte > 1 &&
    scheda.gruppi.every((g) => !g.tip);
  // Piu' strumenti aperti: si possono decidere tutti insieme, con la stessa
  // risposta. Ognuno resta una cosa a se' (propria issue); chi ne vuole solo
  // alcuni usa i moduli dei singoli strumenti.
  const strumentiAperti = scheda.gruppi.filter(
    (g) => g.tip && g.tip.stato === "pending",
  );
  // Tutto il contenuto in una decisione sola, anche quando c'e' uno strumento:
  // l'issue e' quella dello strumento (o della prima tip) e tutto il resto,
  // utilizzi e capitoli, ci finisce dentro come linee guida.
  const decidiInBlocco = onDecidiPacchetto !== null && !pacchetto && aperte > 1;
  // Con piu' strumenti si sceglie anche come aprire le issue.
  const perStrumento = onDecidiTutti !== null && strumentiAperti.length > 1;
  const [modo, setModo] = useState("una");
  // Il canonico quando c'e': e' l'indirizzo che apre QUESTO post invece del
  // lettore di reel. Il grezzo resta come ripiego per le fonti non-Instagram.
  const apri = hrefSicuro(scheda.url_canonico || scheda.url);
  // Una volta che il materiale e' arrivato la richiesta e' soddisfatta: il
  // post continua a promettere un file, ma tu gliel'hai gia' dato. Tenere
  // l'etichetta rossa farebbe sembrare da fare una cosa fatta.
  const servito = lavoro?.stato === "finita";
  return (
    <section className="p-4">
      <header className="mb-4">
        <div className="flex flex-wrap items-start gap-3">
          <h2 className="flex-1 text-lg font-semibold">
            {scheda.titolo || scheda.source_id}
          </h2>
          {/* Deciso tutto, il passo successivo sta anche in cima: non si
              scorre fino in fondo per andare avanti. */}
          {onProssimo && aperte === 0 && (
            <Button size="sm" onClick={onProssimo}>
              Prossimo contenuto
            </Button>
          )}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
          <Badge>{scheda.stato_etichetta}</Badge>
          <Consigliato valore={scheda.consigliato} />
          <span>{origine(scheda.origine)}</span>
          {apri && (
            <a
              href={apri}
              target="_blank"
              rel="noreferrer"
              className="underline"
            >
              fonte
            </a>
          )}
          {scheda.esito && <span>{scheda.esito}</span>}
        </div>
      </header>

      {/* Due avvisi, non uno. Il primo chiede un'azione a te, il secondo
          dichiara una cosa che non sappiamo ancora fare noi: fusi insieme,
          mandavano ad aprire un post che non chiedeva niente. */}
      {scheda.manca_allegato && (
        <section
          className={`mb-4 rounded-lg border bg-surface-2 p-4 ${
            servito ? "border-border" : "border-warning/40"
          }`}
        >
          <div className="flex flex-wrap items-center gap-2">
            <Badge state={servito ? undefined : "danger"}>
              {servito ? "materiale aggiunto" : "manca link/documento"}
            </Badge>
            <h3 className="font-medium">
              {servito
                ? "Il file che mancava è arrivato"
                : "Il post promette un file"}
            </h3>
          </div>
          <p className="mt-1 text-sm text-muted">
            {servito ? (
              "Le tip qui sotto tengono già conto di quello che hai caricato. Se ne hai altro, aggiungilo pure."
            ) : (
              <>
                Lo consegna solo dopo un&apos;azione (un commento, un
                messaggio), e commentare richiede di essere loggato. Fallo da
                qui: il link qui sotto apre <em>questo</em> post e non il
                lettore di reel, che da loggato scorre e ti porta altrove.
              </>
            )}
          </p>
          {apri && !servito && (
            <a
              className="mt-3 inline-block underline"
              href={apri}
              target="_blank"
              rel="noreferrer"
            >
              Apri il post
            </a>
          )}
          {onMateriale && (
            <Materiale
              sourceId={scheda.source_id}
              onInvia={onMateriale}
              lavoro={lavoro}
              inCorso={inCorso}
            />
          )}
        </section>
      )}

      {/* Sempre disponibile: un commento puo' sbloccare altre informazioni
          anche su un post che sembrava completo. Appena arrivano, la scheda
          si rielabora con quelle in piu'. */}
      {onMateriale && !scheda.manca_allegato && (
        <details className="mb-4 rounded-lg border border-border p-3">
          <summary className="cursor-pointer text-sm font-medium">
            Aggiungi altre fonti
          </summary>
          <Materiale
            sourceId={scheda.source_id}
            onInvia={onMateriale}
            lavoro={lavoro}
            inCorso={inCorso}
          />
        </details>
      )}

      {scheda.da_leggere_immagini && (
        <section className="mb-4 rounded-lg border border-border bg-surface-2 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>da leggere nelle immagini</Badge>
            <h3 className="font-medium">Il contenuto sta nelle slide</h3>
          </div>
          <p className="mt-1 text-sm text-muted">
            Non c&apos;è un parlato da ascoltare: il livello 2 legge
            l&apos;audio e qui non c&apos;è. Non serve niente da parte tua — è
            una capacità che ci manca.
          </p>
          {apri && (
            <a
              className="mt-3 inline-block underline"
              href={apri}
              target="_blank"
              rel="noreferrer"
            >
              Guarda il post
            </a>
          )}
        </section>
      )}

      <div className="grid gap-4">
        {pacchetto && (
          <section className="grid gap-2 rounded-xl border border-border bg-surface-2 p-4">
            <h3 className="font-semibold">
              {scheda.titolo}: {aperte} capitoli, una sola decisione
            </h3>
            <p className="text-sm text-muted">
              Approvandola la prendi intera: i capitoli qui sotto diventano le
              linee guida con cui la implemento, in un&apos;unica issue.
            </p>
            <Decisione
              entita={scheda.entita}
              tip={{ id: `tutto-${scheda.source_id}` }}
              inCorso={inCorso}
              onDecidi={(corpo) => onDecidiPacchetto(corpo)}
            />
          </section>
        )}
        {decidiInBlocco && (
          <section className="grid gap-2 rounded-xl border border-border bg-surface-2 p-4">
            <h3 className="font-semibold">
              Decidi tutto insieme: {aperte} tip
            </h3>
            {perStrumento && (
              <div className="flex flex-wrap gap-2" role="group" aria-label="come aprire le issue">
                {[["una", "Una sola issue"], ["strumenti", `Un'issue per ognuno dei ${strumentiAperti.length} strumenti`]].map(([v, et]) => (
                  <Button key={v} variant="ghost" size="sm" type="button" aria-pressed={modo === v}
                    onClick={() => setModo(v)} className={`rounded-md border px-3 py-1 text-sm transition-colors ${modo === v ? "border-info/60 bg-info/15 font-medium" : "border-border text-muted hover:bg-surface"}`}>
                    {et}
                  </Button>
                ))}
              </div>
            )}
            <p className="text-sm text-muted">
              {modo === "strumenti" && perStrumento
                ? "Stessa risposta per tutti, ognuno con la sua issue (e i suoi utilizzi)."
                : "Una sola issue, quella dello strumento (o della prima tip); le altre — utilizzi e capitoli — ci finiscono dentro come linee guida per implementarlo."}{" "}
              Per scegliere pezzo per pezzo, decidi qui sotto.
            </p>
            <Decisione
              entita={scheda.entita}
              tip={{ id: `tutto-${scheda.source_id}` }}
              inCorso={inCorso}
              onDecidi={(corpo) =>
                modo === "strumenti" && perStrumento
                  ? onDecidiTutti(corpo)
                  : onDecidiPacchetto(corpo)
              }
            />
          </section>
        )}
        {scheda.gruppi.map((g) => (
          <Gruppo
            key={g.strumento}
            gruppo={g}
            inCorso={inCorso}
            onDecidiStrumento={onDecidiStrumento}
            onDecidiTip={onDecidiTip}
            entita={scheda.entita}
            soloLettura={pacchetto}
          />
        ))}

        {scheda.pratiche.length > 0 && (
          <section className="grid gap-3">
            {/* Titolo solo quando c'e' anche un gruppo: su un contenuto fatto
                di sole pratiche, "Pratiche" sopra l'unica sezione della
                pagina non distingue niente da niente. */}
            {scheda.gruppi.length > 0 && (
              <h3 className="text-xs font-medium uppercase tracking-wide text-muted">
                Pratiche, che non appartengono a nessuno strumento
              </h3>
            )}
            {scheda.pratiche.map((t) => (
              <Tip key={t.id} tip={t}>
                {t.stato === "pending" && !pacchetto && (
                  <Decisione
                    entita={scheda.entita}
                    tip={t}
                    inCorso={inCorso}
                    onDecidi={(corpo) => onDecidiTip(t.id, corpo)}
                  />
                )}
              </Tip>
            ))}
          </section>
        )}

        {scheda.tip.length === 0 && (
          <p className="text-muted">
            Questo contenuto non ha prodotto nessuna tip.
            {scheda.esito ? ` ${scheda.esito}` : ""}
          </p>
        )}
      </div>

      <Storico key={scheda.source_id} sourceId={scheda.source_id} />

      {issueUrls.length > 0 && (
        <ul className="mt-4 grid gap-1 text-sm">
          {issueUrls.map((url) => {
            const href = hrefSicuro(url);
            return (
              <li key={url}>
                {href ? (
                  <a
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    className="underline"
                  >
                    {url}
                  </a>
                ) : (
                  url
                )}
              </li>
            );
          })}
        </ul>
      )}

      <footer className="mt-4 flex flex-wrap items-center gap-3 border-t border-border pt-4">
        <span className="text-sm text-muted">
          {aperte === 0
            ? "Tutto deciso su questo contenuto."
            : `Restano ${aperte} da decidere.`}
        </span>
        {onProssimo && (
          <Button size="sm" onClick={onProssimo} disabled={aperte > 0}>
            Prossimo contenuto
          </Button>
        )}
      </footer>
    </section>
  );
}
