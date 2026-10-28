import { useCallback, useEffect, useState } from "react";
import { Button, Input } from "@suite/design-system";
import { useEsiti, STATI } from "../hooks/useEsiti";
import { ETICHETTA_STATO, PUNTO_STATO } from "../lib/stati";
import CategoriaStrumenti from "./CategoriaStrumenti";

function Chip({ attivo, onClick, children }) {
  return (
    <Button
      variant="ghost"
      aria-pressed={attivo}
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-info ${
        attivo ? "border-border bg-surface font-medium text-text" : "border-border bg-surface text-muted hover:bg-surface-2 hover:text-text"
      }`}
    >
      {children}
    </Button>
  );
}

const idDaHash = () => {
  const m = /^#\/esiti\/(.+)$/.exec(window.location.hash);
  return m ? decodeURIComponent(m[1]) : null;
};

/** Which rows are open. The open one that was linked lives in the hash
 *  (`#/esiti/<id>`), so a link lands straight on the tool. */
function useAperti() {
  const [aperti, setAperti] = useState(() => {
    const id = idDaHash();
    return new Set(id ? [id] : []);
  });
  useEffect(() => {
    const su = () => {
      const id = idDaHash();
      if (id) setAperti((a) => (a.has(id) ? a : new Set(a).add(id)));
    };
    window.addEventListener("hashchange", su);
    return () => window.removeEventListener("hashchange", su);
  }, []);
  const alterna = useCallback((id) => {
    setAperti((a) => {
      const n = new Set(a);
      if (n.has(id)) n.delete(id); else n.add(id);
      return n;
    });
    if (idDaHash() === id) window.location.hash = "#/esiti";
    else window.location.hash = `#/esiti/${encodeURIComponent(id)}`;
  }, []);
  return { aperti, alterna, setAperti };
}

/** Jumps to a category without touching the hash, which holds the view. */
const vaiA = (key) =>
  document.getElementById(`categoria-${key || "senza"}`)?.scrollIntoView?.({ block: "start", behavior: "smooth" });

/** «Strumenti»: every tool we adopted, grouped by category; each one opens
 *  on what it does and on its story. */
export default function Esiti({ istanza = "" }) {
  const {
    visibili, perCategoria, conteggi, caricamento, errore, stato, setStato,
    ricerca, setRicerca, inSync, esitoSync, sincronizza, anomalie, erroreAnomalie,
  } = useEsiti(istanza);
  const { aperti, alterna, setAperti } = useAperti();
  const tuttiAperti = visibili.length > 0 && visibili.every((e) => aperti.has(e.id));
  const alternaTutti = () => setAperti(tuttiAperti ? new Set() : new Set(visibili.map((e) => e.id)));

  // A linked tool must be on screen, not just open somewhere below the fold.
  const [linkato, setLinkato] = useState(idDaHash);
  useEffect(() => {
    const su = () => setLinkato(idDaHash());
    window.addEventListener("hashchange", su);
    return () => window.removeEventListener("hashchange", su);
  }, []);
  useEffect(() => {
    if (!linkato || caricamento) return;
    document.getElementById(`esito-${linkato}`)?.scrollIntoView?.({ block: "start" });
  }, [linkato, caricamento]);

  return (
    <section className="px-4 pb-10">
      {anomalie.length > 0 && (
        <div role="alert" className="mb-3 rounded-lg border border-danger bg-danger/10 p-3 text-sm text-danger">
          <p className="font-semibold">
            {anomalie.length === 1
              ? "1 anomalia: un'adozione non regge"
              : `${anomalie.length} anomalie: ci sono adozioni che non reggono`}
          </p>
          <ul className="mt-1 list-disc pl-5">
            {anomalie.map((a) => <li key={`${a.tipo}-${a.riferimento}`}>{a.messaggio}</li>)}
          </ul>
        </div>
      )}
      {erroreAnomalie && (
        <p className="mb-3 text-sm text-warning">
          Non riesco a controllare le anomalie: {erroreAnomalie}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2" aria-label="Filtra per stato">
        <Chip attivo={stato === "tutti"} onClick={() => setStato("tutti")}>
          tutti <span className="font-semibold tabular-nums">{conteggi.tutti}</span>
        </Chip>
        {STATI.map((s) => (
          <Chip key={s} attivo={stato === s} onClick={() => setStato(s)}>
            <span aria-hidden className={`h-2 w-2 rounded-full ${PUNTO_STATO[s]}`} />
            {ETICHETTA_STATO[s]} <span className="font-semibold tabular-nums">{conteggi[s]}</span>
          </Chip>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Input
          type="search"
          value={ricerca}
          onChange={(ev) => setRicerca(ev.target.value)}
          placeholder="Cerca: nome, a cosa serve, comando, nodo…"
          aria-label="Cerca"
          className="min-w-0 flex-1 basis-56 bg-surface"
        />
        <Button variant="secondary" disabled={visibili.length === 0} onClick={alternaTutti}>
          {tuttiAperti ? "Chiudi tutti" : "Apri tutti"}
        </Button>
        <Button variant="secondary" disabled={inSync} onClick={sincronizza}>
          {inSync ? "Aggiorno…" : "Aggiorna da GitHub"}
        </Button>
      </div>
      {perCategoria.length > 1 && (
        <nav aria-label="Vai alla categoria" className="mt-3 flex flex-wrap gap-1.5">
          {perCategoria.map((g) => (
            <Button
              key={g.key || "senza"}
              variant="ghost"
              size="sm"
              onClick={() => vaiA(g.key)}
              className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted transition-colors hover:bg-surface-2 hover:text-text focus-visible:outline-2 focus-visible:outline-info"
            >
              {g.nome} · <span className="tabular-nums">{g.esiti.length}</span>
            </Button>
          ))}
        </nav>
      )}
      {esitoSync && (
        <div className="mt-3 rounded-lg border border-border p-3 text-sm" role="status">
          {esitoSync.errore ? (
            <p className="text-danger">Aggiornamento non riuscito: {esitoSync.errore}</p>
          ) : (
            <p>
              {esitoSync.cambiati.length === 0
                ? "Tutto già aggiornato."
                : `Aggiornati: ${esitoSync.cambiati.map((c) => c.id).join(", ")}.`}
            </p>
          )}
          {esitoSync.problemi.length > 0 && (
            <ul className="mt-1 text-warning">
              {esitoSync.problemi.map((p) => <li key={p}>{p}</li>)}
            </ul>
          )}
        </div>
      )}
      {caricamento && <p className="py-6 text-muted">Caricamento…</p>}
      {errore && <p className="py-6 text-danger">Non riesco a leggere gli esiti: {errore}</p>}
      {!caricamento && !errore && visibili.length === 0 && (
        <p className="py-6 text-muted">
          {conteggi.tutti === 0
            ? "Nessuno strumento adottato finora."
            : "Nessuno strumento corrisponde ai filtri."}
        </p>
      )}
      {perCategoria.map((g) => (
        <CategoriaStrumenti key={g.key || "senza"} gruppo={g} aperti={aperti} alterna={alterna} mostraIstanza={!istanza} />
      ))}
    </section>
  );
}
