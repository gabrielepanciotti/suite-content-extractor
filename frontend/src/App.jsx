import { useEffect, useState } from "react";
import { Button } from "@suite/design-system";
import Elenco, { visibiliOrdinati } from "./components/Elenco";
import Scheda from "./components/Scheda";
import Riassunto from "./components/Riassunto";
import Esiti from "./components/Esiti";
import SceltaIstanza from "./components/SceltaIstanza";
import { useContenuti } from "./hooks/useContenuti";
import { useIstanze } from "./hooks/useIstanze";
import { useScheda } from "./hooks/useScheda";

function Pannello({ sourceId, onChiudi = null, onDeciso, onProssimo }) {
  const {
    scheda, caricamento, errore, problemi, issueUrls, inCorso,
    decidiUnaTip, decidiUnoStrumento, decidiIlPacchetto, decidiTuttiStrumenti, cambiaLEntita, lavoro, mandaMateriale,
  } = useScheda(sourceId);

  // The list carries the derived content state, so it is re-read after every
  // decision: left stale it would show "da vedere" on something decided.
  // Una fonte aggiunta che finisce (o muore) cambia le tip e l'etichetta
  // nell'elenco: senza questo resterebbe «rielaborazione…» fino al ricaricamento.
  const statoLavoro = lavoro?.stato;
  useEffect(() => {
    if (statoLavoro === "finita" || statoLavoro === "fallita") onDeciso();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statoLavoro]);

  const conRicarica = (fn) => async (...args) => {
    if (await fn(...args)) onDeciso();
  };

  return (
    <section className="grid gap-4 bg-surface xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="min-w-0 [overflow-wrap:anywhere] xl:order-1">
      {onChiudi && (
        <div className="flex items-center justify-between px-4 pt-4">
          <p className="text-sm text-muted">{sourceId}</p>
          <Button variant="link" size="sm" className="text-sm" onClick={onChiudi}>
            Chiudi
          </Button>
        </div>
      )}
      {caricamento && <p className="p-4 text-muted">Caricamento…</p>}
      {errore && <p className="p-4 text-danger">Non riesco a leggere la scheda: {errore}</p>}
      {problemi.length > 0 && (
        // Problems are not failures: the decision was recorded, something
        // around it (the note, the issue) was not. Saying so beats silence.
        <ul className="mx-4 mt-2 rounded-lg border border-border p-3 text-sm text-warning">
          {problemi.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      )}
      {scheda && (
        <Scheda
          scheda={scheda}
          inCorso={inCorso}
          issueUrls={issueUrls}
          onDecidiTip={conRicarica(decidiUnaTip)}
          onDecidiStrumento={conRicarica(decidiUnoStrumento)}
          onDecidiPacchetto={conRicarica(decidiIlPacchetto)}
          onDecidiTutti={conRicarica(decidiTuttiStrumenti)}
          onCambiaEntita={cambiaLEntita}
          onProssimo={onProssimo}
          lavoro={lavoro}
          onMateriale={mandaMateriale}
        />
      )}
      </div>
      {/* A destra, a colpo d'occhio: cosa propone. Sopra la scheda sui
          telefoni, dove non c'e' una colonna da affiancare. */}
      {scheda && (
        <aside className="order-first px-4 pt-4 xl:sticky xl:top-4 xl:order-2 xl:self-start xl:px-0 xl:pr-4">
          <Riassunto scheda={scheda} />
        </aside>
      )}
    </section>
  );
}

const VISTE = [["contenuti", "Contenuti"], ["esiti", "Strumenti adottati"]];
const vistaDaHash = () => (window.location.hash.startsWith("#/esiti") ? "esiti" : "contenuti");

/** The view lives in the URL hash: linkable, and Back works. */
function useVista() {
  const [vista, setVista] = useState(vistaDaHash);
  useEffect(() => {
    const su = () => setVista(vistaDaHash());
    window.addEventListener("hashchange", su);
    return () => window.removeEventListener("hashchange", su);
  }, []);
  const vai = (v) => {
    window.location.hash = v === "esiti" ? "#/esiti" : "#/";
  };
  return [vista, vai];
}

function Schede({ vista, onVai }) {
  return (
    <nav aria-label="Viste" className="flex gap-1 px-4">
      {VISTE.map(([v, et]) => (
        <Button key={v} variant="ghost" size="sm" type="button"
          aria-current={vista === v ? "page" : undefined} onClick={() => onVai(v)}
          className={`rounded-lg border px-3 py-1.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-info ${vista === v ? "border-info bg-info/15 text-text font-medium" : "border-border text-muted hover:bg-surface-2"}`}>
          {et}
        </Button>
      ))}
    </nav>
  );
}

export default function App() {
  const [vista, vaiA] = useVista();
  const istanze = useIstanze();
  const { schede, caricamento, errore, ricarica } = useContenuti(istanze.scelta);
  const [correnteId, setCorrenteId] = useState(null);
  const [solo, setSolo] = useState("da_decidere");
  const [ordine, setOrdine] = useState("efficacia");
  // «Prossimo» sull'ultimo contenuto da decidere: non c'e' un altro verso cui
  // andare, e restare fermi sembra un bottone rotto. Si dice che e' finita.
  const [fine, setFine] = useState(false);

  // Si apre sul primo contenuto da decidere; poi resta dove sei, anche a
  // decisione presa (il «Prossimo» si preme a mano).
  useEffect(() => {
    // Cambiata l'istanza, il contenuto aperto puo' non farne parte.
    if (correnteId && schede.length > 0 && !schede.some((s) => s.source_id === correnteId)) {
      setCorrenteId(null);
      return;
    }
    if (!correnteId && schede.length > 0) {
      const primo = visibiliOrdinati(schede, "da_decidere", ordine, null)[0] || schede[0];
      setCorrenteId(primo.source_id);
    }
  }, [correnteId, schede]);

  // Finche' una rielaborazione e' in corso l'etichetta si aggiorna da sola.
  const inCorso = schede.some((s) => s.in_rielaborazione);
  useEffect(() => {
    if (!inCorso) return undefined;
    const t = setInterval(ricarica, 10000);
    return () => clearInterval(t);
  }, [inCorso, ricarica]);

  const apri = (id) => {
    setFine(false);
    setCorrenteId(id);
    window.scrollTo({ top: 0 });
  };
  const prossimo = () => {
    // Lo stesso ordine dell'elenco: «prossimo» e le frecce vanno nello stesso verso.
    const ordinati = visibiliOrdinati(schede, "da_decidere", ordine, correnteId);
    const dopo = ordinati.find((s) => s.source_id !== correnteId && s.stato === "da_vedere");
    if (dopo) apri(dopo.source_id);
    else setFine(true);
  };

  return (
    <main className="mx-auto max-w-screen-2xl pb-16">
      <header className="flex flex-wrap items-center justify-between gap-2 px-4 pt-4 pb-2">
        <h1 className="text-xl font-semibold">
          {vista === "esiti" ? "Strumenti adottati" : "Contenuti"}
        </h1>
        <SceltaIstanza
          istanze={istanze.istanze}
          scelta={istanze.scelta}
          onScegli={(id) => {
            // The open content may not belong to the new instance: start over.
            setCorrenteId(null);
            istanze.setScelta(id);
          }}
          errore={istanze.errore}
        />
      </header>
      <Schede vista={vista} onVai={vaiA} />
      {vista === "esiti" && <Esiti istanza={istanze.scelta} />}
      {vista === "contenuti" && <>
      {caricamento && schede.length === 0 && <p className="p-6 text-muted">Caricamento…</p>}
      {/* An error is said out loud: a silent empty page reads as "nothing
          was ever ingested", which is a different fact entirely. */}
      {errore && <p className="p-6 text-danger">Non riesco a leggere l'elenco: {errore}</p>}
      {!errore && schede.length === 0 && !caricamento && (
        <p className="p-6 text-muted">
          {istanze.scelta
            ? `Nessun contenuto nell'istanza ${istanze.scelta}.`
            : "Nessun contenuto caricato finora."}
        </p>
      )}
      {!errore && schede.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[22rem_1fr]">
          <aside className="border-border lg:sticky lg:top-0 lg:h-screen lg:self-start lg:border-r">
            <Elenco
              schede={schede}
              correnteId={correnteId}
              onApri={apri}
              solo={solo}
              onSolo={setSolo}
              ordine={ordine}
              onOrdine={setOrdine}
              mostraIstanza={!istanze.scelta}
            />
          </aside>
          <div className="min-w-0">
            {fine && (
              <div className="px-4 py-12 text-center">
                <p className="text-lg font-semibold">Hai deciso tutto.</p>
                <p className="mt-1 text-muted">
                  Non ci sono altri contenuti da decidere.
                </p>
                <Button
                  className="mt-4"
                  variant="secondary"
                  onClick={() => {
                    setSolo("tutti");
                    setFine(false);
                  }}
                >
                  Mostra tutti i contenuti
                </Button>
              </div>
            )}
            {correnteId && !fine && (
              <Pannello
                key={correnteId}
                sourceId={correnteId}
                onDeciso={ricarica}
                onProssimo={prossimo}
              />
            )}
          </div>
        </div>
      )}
      </>}
    </main>
  );
}
