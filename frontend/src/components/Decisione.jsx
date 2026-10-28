import { useBozza } from "../hooks/useBozza";
import { Button, Input, Textarea } from "@suite/design-system";
const REPO_DELL_ENTITA = { Life: "Life", "Life work": "life-work", "Life personal": "life-personal" };
import SceltaProgetti from "./SceltaProgetti";
import EntitaLife from "./EntitaLife";

/** Approva o declina UNA cosa — uno strumento, un utilizzo, una pratica.
 *
 *  I due bottoni non decidono da soli: aprono il modulo con il verdetto gia'
 *  scelto. Il motivo e' facoltativo: vuoto vale «per il motivo del giudizio»,
 *  che il backend scrive nel record al suo posto. La nota compare
 *  solo approvando, perche' e' cio' che finisce nell'issue — su uno scarto
 *  non si apre niente, e un campo "come implementarlo" li' chiederebbe di
 *  progettare una cosa che non si fara'.
 */
export default function Decisione({ tip, onDecidi, cascata = false, inCorso = false, entita: entitaIniziale = null }) {
  // Tutto cio' che scrivi qui sta nel browser fino all'invio riuscito: un
  // ricaricamento della pagina non cancella una nota scritta a meta'.
  const [bozza, imposta, svuota] = useBozza(`decisione:${tip.id}`, {
    verdetto: null,
    motivo: "",
    nota: "",
    // Da dove e' arrivato il contenuto; qui si puo' cambiare.
    entita: entitaIniziale,
    repos: [],
  });
  const { verdetto, motivo, nota, repos, entita } = bozza;
  const setVerdetto = (v) => imposta({ verdetto: v });
  const setMotivo = (v) => imposta({ motivo: v });
  const setNota = (v) => imposta({ nota: v });
  const setRepos = (v) => imposta({ repos: v });
  const setEntita = (v) => imposta({ entita: v });

  const chiudi = () => {
    setVerdetto(null);
  };

  const conferma = () => {
    // La bozza si cancella solo se l'invio e' riuscito: se fallisce, quello
    // che avevi scritto e' ancora li'.
    Promise.resolve(
      onDecidi({
        verdict: verdetto,
        reason: motivo.trim(),
        nota: verdetto === "adopted" ? nota.trim() || null : null,
        repos: verdetto === "adopted" ? repos : [],
        entita: verdetto === "adopted" ? entita : null,
      }),
    ).then(svuota, () => {});
  };

  if (!verdetto) {
    return (
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="primary"
          onClick={() => setVerdetto("adopted")}
        >
          Approva
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => setVerdetto("rejected")}
        >
          Declina
        </Button>
        {cascata && (
          // Detto PRIMA di cliccare, non dopo: e' la differenza fra decidere
          // una cosa e deciderne cinque, e si scopre troppo tardi se la
          // pagina lo annuncia solo a cascata avvenuta.
          <span className="text-xs text-muted">
            vale anche per tutti i suoi utilizzi ancora aperti
          </span>
        )}
      </div>
    );
  }

  const approvando = verdetto === "adopted";
  return (
    <div className="mt-3 grid gap-2 rounded-lg border border-border bg-surface-2 p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">
        {approvando ? "Approva" : "Declina"}
        {cascata
          ? " — e con lui tutti i suoi utilizzi ancora aperti, ognuno nel proprio progetto"
          : ""}
      </p>
      <Input
        aria-label="motivo"
        placeholder="Perché (facoltativo: se lo lasci vuoto vale il motivo del giudizio)"
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
        autoFocus
      />
      {approvando && (
        <>
          <Textarea
            aria-label="come implementarlo"
            rows={4}
            placeholder="Come implementarlo, e cosa aggiungi tu — va in cima all'issue"
            value={nota}
            onChange={(e) => setNota(e.target.value)}
          />
          <div className="grid gap-2">
            <p className="text-xs font-medium text-muted">Dove lo mettiamo?</p>
            <EntitaLife valore={entita} onCambia={setEntita} />
            <p className="text-xs text-muted">
              Poi, se vuoi, un progetto preciso (altrimenti basta l&apos;entità):
            </p>
          </div>
          <SceltaProgetti scelti={repos} onCambia={setRepos} />
          {repos.length === 0 && (
            <p className="text-xs text-muted">
              {entita
                ? `Nessun progetto indicato: l'issue va in ${REPO_DELL_ENTITA[entita]} (${entita}).`
                : "Nessun progetto e nessuna entità: la decisione viene registrata ma non nasce nessuna issue."}
            </p>
          )}
        </>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="secondary"
          className="border-info/60 bg-info/15 hover:bg-info/25"
          onClick={conferma}
          loading={inCorso}
          disabled={inCorso}
        >
          Conferma
        </Button>
        <Button size="sm" variant="ghost" onClick={chiudi} disabled={inCorso}>
          Annulla
        </Button>
      </div>
    </div>
  );
}
