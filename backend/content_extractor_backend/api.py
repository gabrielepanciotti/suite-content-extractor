"""Le rotte. Cablaggio e nient'altro: il significato sta in schede.py.

Ogni decisione passa dal Reviewer che usa anche la CLI — stessa nota nel brain,
stessa issue, stesso ordine (coda risolta prima di ogni artefatto). Due strade
per decidere divergerebbero al primo bug corretto da una parte sola.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from suite_backend_core.github_client import GhIssueCreator, SubprocessCommandRunner

from suite_learn_core.contents import ContentRegistry, JsonlContentRegistry
from suite_learn_core.decisions import FileNoteWriter, Verdict
from suite_learn_core.esiti import (
    Anomalia,
    EsitiStore,
    EsitoConContenuto,
    GhIssueReader,
    IssueReader,
    JsonEsitiStore,
    con_contenuto,
    ordina,
    sync as sync_esiti,
    verifica,
)
from suite_learn_core.queue import JsonlQueue, Proposal, ProposalQueue
from suite_learn_core.review import (
    NOT_REGISTERED,
    AmbiguousPrefix,
    DecisionOutcome,
    RepoChecker,
    Reviewer,
    UnknownProposal,
    find_by_prefix,
)

from . import instances as ist
from .materiale import (
    Lanciatore,
    LanciatoreStaccato,
    MaterialeRifiutato,
    aggiorna_da_log,
    avvia,
    leggi_lavoro,
    salva_file,
    vivo,
)
from .repos import Repo, RepoCheckerCache, conosciuti, con_esistenza, risolvi
from .schede import Gruppo, SchedaCompleta, Sintesi, elenco, scheda

NODE_ID = os.environ.get("LEARN_NODE_ID", "contentExtractor")

router = APIRouter(prefix="/api")


def queue_root() -> Path:
    """Radice della coda: env, altrimenti derivata dal file. Mai un assoluto."""
    env = os.environ.get("LEARN_QUEUE_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / ".learn-queue"


def get_queue() -> ProposalQueue:
    return JsonlQueue(queue_root())


def get_registry() -> ContentRegistry:
    return JsonlContentRegistry(queue_root())


def get_esiti() -> EsitiStore:
    return JsonEsitiStore(queue_root(), NODE_ID)


def get_issue_reader() -> IssueReader:
    """`gh` vero: sovrascritto nei test, dove non deve mai partire."""
    return GhIssueReader()


_CHECKER = RepoCheckerCache()


def get_repo_checker() -> RepoChecker:
    """Il verificatore di repo vero (`gh repo view`, con cache a scadenza).

    Sovrascritto nei test, dove `gh` non deve mai partire.
    """
    return _CHECKER


def get_reviewer() -> Reviewer:
    """Il Reviewer vero, costruito ESATTAMENTE come lo costruisce la CLI.

    Sovrascritto nei test: qui dentro ci sono `gh` e il filesystem, che in un
    test non devono mai partire. Il fallback_dir non e' un dettaglio: se `gh`
    manca, l'issue viene scritta su file invece di perdersi, ed e' la ragione
    per cui GhIssueCreator non solleva mai.
    """
    root = queue_root()
    return Reviewer(
        get_queue(),
        FileNoteWriter(root.parent),
        GhIssueCreator(
            SubprocessCommandRunner(), fallback_dir=root / "issues-non-create"
        ),
        date.today().isoformat(),
        esiti=get_esiti(),
        checker=get_repo_checker(),
    )


# --- Istanze (ContentExtractor#4, spec Life 2026-10-14 §4) -----------------


def _default_istanza() -> str | None:
    """Il default del device per le righe senza istanza; None se il registro non si legge."""
    try:
        return ist.default_id()
    except ist.RegistroNonDisponibile:
        return None


def _scheda(queue: ProposalQueue, registry: ContentRegistry, source_id: str):
    return scheda(queue, registry, NODE_ID, source_id, _default_istanza())


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, ist.IstanzaSconosciuta):
        if not exc.istanza:
            return HTTPException(422, {
                "error": "instance_required",
                "message": "il device serve piu' istanze e nessuna e' il default: dichiara `instance`",
                "valid": exc.validi,
            })
        return HTTPException(422, {
            "error": "instance_unknown",
            "message": str(exc),
            "valid": exc.validi,
        })
    return HTTPException(503, f"registro delle istanze non disponibile: {exc}")


def _lettura(instance: str | None) -> str | None:
    try:
        return ist.per_lettura(instance)
    except (ist.IstanzaSconosciuta, ist.RegistroNonDisponibile) as exc:
        raise _http(exc) from exc


def _scrittura(instance: str | None, del_record: str | None = None) -> str:
    """L'istanza di una scrittura, validata; e deve essere quella del record toccato.

    Una decisione dichiarata per un'istanza su un contenuto di un'altra e' un
    errore di chi chiama, non qualcosa da riattribuire in silenzio.
    """
    if not instance and del_record:
        return del_record
    try:
        scelta = ist.per_scrittura(instance)
    except (ist.IstanzaSconosciuta, ist.RegistroNonDisponibile) as exc:
        raise _http(exc) from exc
    if del_record and scelta != del_record:
        raise HTTPException(422, {
            "error": "instance_mismatch",
            "message": f"il contenuto appartiene all'istanza {del_record!r}, non a {scelta!r}",
            "valid": [del_record],
        })
    return scelta


def _istanza_proposta(proposal: Proposal) -> str | None:
    return proposal.instance_id or _default_istanza()


Istanza = Annotated[str | None, Query(description="id d'istanza; assente = tutte")]


class VistaIstanza(BaseModel):
    id: str
    status: Literal["ok", "unreachable"]
    reason: str | None = None
    default: bool = False
    profile: str = ""
    channels: dict = {}
    channel_problems: list[str] = []


@router.get("/instances", response_model=list[VistaIstanza])
def istanze() -> list[VistaIstanza]:
    """Le istanze servite: quelle irraggiungibili compaiono con il motivo, non spariscono."""
    try:
        return [VistaIstanza(**v.__dict__) for v in ist.elenco()]
    except ist.RegistroNonDisponibile as exc:
        raise _http(exc) from exc


class Decisione(BaseModel):
    # Letterale, non str: un verdetto illegale (es. "adopt" invece di
    # "adopted") deve fermarsi qui, con un 422 di FastAPI, PRIMA che la
    # richiesta arrivi a una riga di codice che tocca la coda. Reviewer.decide
    # risolve la coda prima di validare il verdetto (build_decision_note
    # solleva dopo, non prima) — quindi un verdetto sbagliato passato intatto
    # scriverebbe "status":"adopt" su file, riga che nessun loader rilegge piu'.
    verdict: Verdict
    reason: str = ""
    """Facoltativo: vuoto vale "per il motivo del giudizio" (vedi _motivo)."""
    entita: Literal["Life work", "Life personal", "Life"] | None = None
    """Dove vale: finisce in cima alla nota dell'issue, e chi smista lo legge."""
    nota: str | None = None
    """Come implementarlo, e cosa aggiungere di proprio.

    E' la meta' che scrive una persona: finisce in cima all'issue e nella nota
    di decisione. Il `reason` dice PERCHE' si e' deciso cosi', questa dice COSA
    farne — due domande diverse, due campi.
    """
    instance: str | None = None
    """L'istanza Life della decisione: se manca, quella del contenuto deciso."""
    repos: list[str] | None = None
    """I progetti in cui aprire l'issue.

    Assente: quello indicato dal giudizio. Lista vuota: nessuno — ed e' cio'
    che la pagina promette quando si tolgono tutti i progetti («non nasce
    nessuna issue»). Confondere i due apriva l'issue proprio dove la persona
    l'aveva appena tolta.
    """


class DecisioneLotto(BaseModel):
    entita: Literal["Life work", "Life personal", "Life"] | None = None
    adotta: list[str] = []
    scarta: list[str] = []
    reason: str = ""
    nota: str | None = None
    repos: list[str] | None = None
    instance: str | None = None


class EsitoDecisione(BaseModel):
    ok: bool = True
    problemi: list[str] = []
    issue_urls: list[str] = []
    issue_url: str | None = None
    """La prima delle issue_urls, per chi ne aspetta una sola."""


class LavoroFuori(BaseModel):
    """Lo stato di una ri-estrazione, come lo legge la pagina."""

    source_id: str
    stato: str
    materiale: str
    quando: str | None
    esito: str | None = None


class EsitoLotto(SchedaCompleta):
    problemi: list[str] = []
    issue_urls: list[str] = []


Q = Annotated[ProposalQueue, Depends(get_queue)]
R = Annotated[ContentRegistry, Depends(get_registry)]
Rev = Annotated[object, Depends(get_reviewer)]
Es = Annotated[EsitiStore, Depends(get_esiti)]
Gh = Annotated[IssueReader, Depends(get_issue_reader)]


class EsitoSync(BaseModel):
    cambiati: list[dict] = []
    problemi: list[str] = []
    esiti: list[EsitoConContenuto] = []


def _arricchiti(store: EsitiStore, queue: ProposalQueue, registry: ContentRegistry):
    return [con_contenuto(e, queue, registry) for e in ordina(store.list())]


def _istanza_esito(esito, per_id: dict[str, Proposal]) -> str | None:
    """L'istanza di uno strumento: la sua, o quella della sua prima proposta."""
    if esito.instance_id:
        return esito.instance_id
    for pid in esito.proposte:
        if pid in per_id:
            return _istanza_proposta(per_id[pid])
    return _default_istanza()


@router.get("/esiti", response_model=list[EsitoConContenuto])
def lista_esiti(
    store: Es, queue: Q, registry: R, instance: Istanza = None
) -> list[EsitoConContenuto]:
    filtro = _lettura(instance)
    esiti = _arricchiti(store, queue, registry)
    per_id = {p.id: p for p in queue.list(node_id=NODE_ID)}
    for e in esiti:
        e.instance_id = _istanza_esito(e, per_id)
    if filtro is not None:
        esiti = [e for e in esiti if e.instance_id == filtro]
    return esiti


@router.get("/esiti/anomalie", response_model=list[Anomalia])
def anomalie_esiti(store: Es, queue: Q) -> list[Anomalia]:
    """Cio' che rompe «adottata = almeno un'issue vera»: la pagina lo mostra in rosso."""
    return verifica(queue, store, NODE_ID, queue_root() / "issues-non-create")


@router.post("/esiti/sync", response_model=EsitoSync)
def sincronizza_esiti(
    store: Es, reader: Gh, queue: Q, registry: R
) -> EsitoSync:
    """Riallinea gli esiti con le loro issue: stato e commento di chiusura."""
    risultato = sync_esiti(store, reader, date.today().isoformat())
    return EsitoSync(
        cambiati=risultato.cambiati,
        problemi=risultato.problemi,
        esiti=_arricchiti(store, queue, registry),
    )


@router.get("/repos", response_model=list[Repo])
def repos(checker: Annotated[RepoChecker, Depends(get_repo_checker)]) -> list[Repo]:
    """I progetti in cui si puo' aprire un'issue da qui, per la scelta nella pagina.

    Un repo che su GitHub non esiste e' marcato (`esiste: false`): la pagina lo
    mostra spento, perche' sceglierlo vorrebbe dire un'adozione senza issue.
    """
    return con_esistenza(list(conosciuti()), checker)


@router.get("/contents", response_model=list[Sintesi])
def lista(queue: Q, registry: R, instance: Istanza = None) -> list[Sintesi]:
    righe = elenco(queue, registry, NODE_ID, _default_istanza(), _lettura(instance))
    root = queue_root()
    for riga in righe:
        lavoro = leggi_lavoro(root, riga.source_id)
        # Lo stato vero dal log: finche' lo leggeva solo la scheda aperta, un
        # lavoro finito restava «in corso» e il post tornava a dire che manca
        # il contenuto che avevi appena consegnato.
        if lavoro and lavoro.stato == "in_corso":
            lavoro = aggiorna_da_log(root, lavoro, riga.quante_tip)
        # Il processo c'e' ancora: un lavoro «in corso» il cui processo e'
        # morto non sta rielaborando niente (lo dichiara la scheda).
        riga.in_rielaborazione = bool(
            lavoro and lavoro.stato == "in_corso" and (not lavoro.pid or vivo(lavoro.pid))
        )
        # Il file che mancava e' arrivato: l'etichetta rossa non descrive piu'
        # niente, e resterebbe a dire il contrario di cio' che hai fatto.
        if lavoro and lavoro.stato == "finita":
            riga.materiale_aggiunto = True
            riga.manca_allegato = False
    return righe


def get_lanciatore() -> Lanciatore:
    """Chi avvia davvero il sottoprocesso. Sostituito nei test, che non spendono."""
    return LanciatoreStaccato()


L = Annotated[Lanciatore, Depends(get_lanciatore)]


@router.post("/contents/{source_id:path}/materiale", response_model=LavoroFuori)
def aggiungi_materiale(
    source_id: str,
    queue: Q,
    registry: R,
    lanciatore: L,
    link: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
    instance: Annotated[str | None, Form()] = None,
) -> LavoroFuori:
    """Il file o il link che il post consegnava solo a mano: entra da qui.

    Uno dei due basta, tutti e due insieme no: sono due materiali diversi e
    produrrebbero due estrazioni, non una. Chi ne ha due li carica due volte,
    e le tip si sommano sulla stessa scheda.
    """
    card = _scheda(queue, registry, source_id)
    if card is None:
        raise HTTPException(404, f"nessun contenuto con id {source_id}")
    istanza = _scrittura(instance, card.instance_id)

    pulito = (link or "").strip()
    if bool(pulito) == bool(file):
        raise HTTPException(
            422, "serve un link OPPURE un file, non nessuno dei due e non entrambi"
        )

    root = queue_root()
    try:
        materiale = (
            pulito if pulito
            else str(salva_file(root, source_id, file.filename or "", file.file.read()))
        )
    except MaterialeRifiutato as exc:
        raise HTTPException(422, str(exc)) from exc

    lavoro = avvia(
        root, source_id, materiale,
        node_id=NODE_ID, lanciatore=lanciatore,
        radice_nodo=root.parent, istanza=istanza,
    )
    return LavoroFuori(**lavoro.json())


@router.get("/contents/{source_id:path}/materiale", response_model=LavoroFuori | None)
def stato_materiale(source_id: str, queue: Q, registry: R) -> LavoroFuori | None:
    """A che punto è la ri-estrazione. La pagina lo chiede finché è in corso."""
    root = queue_root()
    lavoro = leggi_lavoro(root, source_id)
    if lavoro is None:
        return None
    card = _scheda(queue, registry, source_id)
    quante = len([t for t in card.tip if t.stato != "failed"]) if card else 0
    return LavoroFuori(**aggiorna_da_log(root, lavoro, quante).json())


class CorpoEntita(BaseModel):
    entita: Literal["Life work", "Life personal", "Life"]
    instance: str | None = None


@router.put("/contents/{source_id:path}/entita", response_model=SchedaCompleta)
def cambia_entita(
    source_id: str, corpo: CorpoEntita, queue: Q, registry: R
) -> SchedaCompleta:
    """L'entità da cui è arrivato il contenuto si può correggere a mano."""
    card = _scheda(queue, registry, source_id)
    if card is None:
        raise HTTPException(404, f"nessun contenuto con id {source_id}")
    _scrittura(corpo.instance, card.instance_id)
    registry.set_entita(source_id, corpo.entita)
    return _scheda(queue, registry, source_id)


class Lettura(BaseModel):
    quando: str | None
    esito: str
    fonte: str | None = None


@router.get("/contents/{source_id:path}/letture", response_model=list[Lettura])
def storico_letture(source_id: str, registry: R) -> list[Lettura]:
    """Ogni lettura finita del contenuto, dalla piu' vecchia: lo storico."""
    storico = getattr(registry, "history", None)
    eventi = storico(source_id) if storico else []
    return [Lettura(
            quando=e.at.isoformat() if e.at else None, esito=e.outcome, fonte=e.fonte
        ) for e in eventi]


@router.get("/contents/{source_id:path}", response_model=SchedaCompleta)
def dettaglio(source_id: str, queue: Q, registry: R) -> SchedaCompleta:
    card = _scheda(queue, registry, source_id)
    if card is None:
        raise HTTPException(404, f"nessun contenuto con id {source_id}")
    return card


def _motivo(proposal: Proposal, verdict: Verdict, reason: str | None) -> str:
    """The reason written in the record: the person's, or the judgement's.

    Asking for a reason every time made the person retype the one already on
    the card whenever they agreed with it. An empty reason now means "for the
    reason you gave": the record still says why — the Reviewer's rule stands —
    and says whose words they are. Deciding AGAINST the judgement without a
    word is still recorded, but plainly as such, not dressed up as agreement.
    """
    scritto = (reason or "").strip()
    if scritto:
        return scritto
    consigliato = {"adopt": "adopted", "skip": "rejected"}.get(
        proposal.item.recommendation
    )
    giudizio = proposal.item.verdict_reason
    if verdict == consigliato and giudizio:
        return f"d'accordo con il giudizio: {giudizio}"
    if verdict == consigliato:
        return "d'accordo con il giudizio"
    return "deciso contro il giudizio, senza un motivo scritto"


def _risolvi(queue: ProposalQueue, source_id: str | None, proposal_id: str) -> Proposal:
    """Trova la proposta e verifica che sia decidibile — senza deciderla.

    Sola lettura: usata come pre-flight del lotto, cosi' un id che non regge
    (sconosciuto, ambiguo, gia' deciso, o di un altro contenuto) ferma l'intero
    lotto prima che una sola decisione venga presa, invece di lasciarne alcune
    fatte e altre no.
    """
    try:
        proposal = find_by_prefix(queue, proposal_id)
    except UnknownProposal as exc:
        raise HTTPException(404, str(exc)) from exc
    except AmbiguousPrefix as exc:
        raise HTTPException(409, str(exc)) from exc
    if source_id is not None and proposal.item.source_id != source_id:
        # Stesso trattamento di un id sconosciuto: in questo scope (questo
        # contenuto) la proposta non risolve, anche se esiste altrove. Un 409
        # e' riservato al vero conflitto di stato (gia' decisa) qui sotto.
        raise HTTPException(
            404,
            f"la proposta {proposal_id} non appartiene al contenuto {source_id}",
        )
    if proposal.status != "pending":
        # Con lo stato attuale nel corpo: il frontend ridisegna da cio' che e'
        # successo davvero invece di indovinare.
        raise HTTPException(409, {"messaggio": "gia' decisa", "stato": proposal.status})
    return proposal


def _destinazioni(proposal: Proposal, scelti: list[str] | None) -> list[str]:
    """Gli `owner/repo` in cui aprire l'issue, mai il testo del giudizio.

    Il giudizio a volte scrive una frase dove va un nome: passata a `gh` cosi'
    com'e', l'approvazione finiva in un'issue su un repo che non esiste.
    Tutto passa da `risolvi`; un nome che non corrisponde a nessun repo resta
    fuori, e se non ne resta nessuno il Reviewer dice che l'issue non c'e'.
    """
    if scelti is None:
        nomi = [proposal.item.target_repo or ""]
    else:
        nomi = [r for r in scelti if r.strip()]
    slug = [r.slug for n in nomi if (r := risolvi(n)) is not None]
    # Vuota se niente si risolve: il Reviewer la legge come «detto: nessuno»
    # e non ripiega sul testo del giudizio, che e' quello che non va a `gh`.
    return list(dict.fromkeys(slug))


# Dove va l'issue quando non si indica nessun progetto: il repo dell'entita'.
# «Life» e' il generale (vale con qualunque strumento, anche fuori da Claude Code);
# le due istanze hanno il loro repo.
REPO_DELL_ENTITA = {
    "Life": "Life",
    "Life work": "life-work",
    "Life personal": "life-personal",
}


class AdozioneBloccata(Exception):
    """Un'adozione che non ha prodotto nessuna issue: la proposta e' ancora pending."""

    def __init__(self, titolo: str, problemi: list[str]) -> None:
        self.titolo = titolo
        self.problemi = problemi
        super().__init__(titolo)


def _bloccate_in_http(bloccate: list[AdozioneBloccata], fatte: int) -> HTTPException:
    """Il 422 leggibile: niente 200 che faccia credere riuscita un'adozione che non lo e'."""
    righe = []
    for b in bloccate:
        motivi = [p for p in b.problemi if p != NOT_REGISTERED] or b.problemi
        righe.append(f"«{b.titolo}» non è stata adottata ({'; '.join(motivi)})")
    testo = ". ".join(righe) + ". Resta in attesa: nessuna issue è stata creata."
    if fatte:
        testo += f" Le altre {fatte} decisioni sono state registrate."
    return HTTPException(422, testo)


def _decidi(
    reviewer,
    proposal: Proposal,
    verdict: Verdict,
    reason: str,
    nota: str | None = None,
    repos: list[str] | None = None,
    entita: str | None = None,
    assorbita_in: list[str] | None = None,
) -> DecisionOutcome:
    if entita and verdict == "adopted":
        nota = f"**Entità Life**: {entita}\n\n{nota or ''}".strip()
    # I repo si passano solo adottando: su uno scarto non si apre niente, e
    # una lista di repo in quel caso descriverebbe un'issue che non esiste.
    adotta = verdict == "adopted"
    if adotta and entita and not [r for r in (repos or []) if r.strip()]:
        # Nessun nodo indicato: basta l'entita'. Il suggerimento del giudizio
        # (spesso ~/.claude) non decide da solo dove va un'idea generale.
        repos = [REPO_DELL_ENTITA[entita]]
    destinazioni = _destinazioni(proposal, repos) if adotta else None
    extra = {"assorbita_in": assorbita_in} if assorbita_in else {}
    esito = reviewer.decide(
        proposal.id, verdict, _motivo(proposal, verdict, reason),
        note=(nota or None) if adotta else None,
        repos=destinazioni,
        **extra,
    )
    if adotta and not esito.adottata:
        raise AdozioneBloccata(proposal.item.title, esito.problems)
    return esito


@router.post("/proposals/{proposal_id}/decision", response_model=EsitoDecisione)
def decidi_una(proposal_id: str, corpo: Decisione, queue: Q, reviewer: Rev) -> EsitoDecisione:
    proposal = _risolvi(queue, None, proposal_id)
    _scrittura(corpo.instance, _istanza_proposta(proposal))
    try:
        esito = _decidi(
            reviewer, proposal, corpo.verdict, corpo.reason, corpo.nota, corpo.repos,
            corpo.entita,
        )
    except AdozioneBloccata as exc:
        raise _bloccate_in_http([exc], 0) from exc
    return EsitoDecisione(
        problemi=esito.problems,
        issue_urls=esito.issue_urls,
        issue_url=esito.issue_url,
    )


@router.post("/contents/{source_id:path}/decision", response_model=EsitoLotto)
def decidi_lotto(
    source_id: str, corpo: DecisioneLotto, queue: Q, registry: R, reviewer: Rev
) -> EsitoLotto:
    # Pre-flight: risolve OGNI id del lotto prima di decidere il primo. Un id
    # che non regge (altro contenuto, gia' deciso, sconosciuto) ferma tutto il
    # lotto qui, a costo zero per il caso ordinario — nessuna issue aperta a
    # meta' lotto, nessuna tip adottata che il chiamante non veda nella
    # risposta di errore.
    da_decidere: list[tuple[Proposal, Verdict]] = [
        (_risolvi(queue, source_id, pid), "adopted") for pid in corpo.adotta
    ] + [
        (_risolvi(queue, source_id, pid), "rejected") for pid in corpo.scarta
    ]
    for proposal, _ in da_decidere:
        _scrittura(corpo.instance, _istanza_proposta(proposal))
    problemi: list[str] = []
    issue_urls: list[str] = []
    bloccate: list[AdozioneBloccata] = []
    for proposal, verdict in da_decidere:
        try:
            esito = _decidi(
                reviewer, proposal, verdict, corpo.reason, corpo.nota, corpo.repos,
                corpo.entita,
            )
        except AdozioneBloccata as exc:
            bloccate.append(exc)
            continue
        problemi.extend(esito.problems)
        issue_urls.extend(esito.issue_urls)
    if bloccate:
        raise _bloccate_in_http(bloccate, len(da_decidere) - len(bloccate))
    # Le tip non nominate restano pending: decidere su alcune e rimandare il
    # resto e' un caso normale, non un errore.
    card = _scheda(queue, registry, source_id)
    if card is None:
        raise HTTPException(404, f"nessun contenuto con id {source_id}")
    return EsitoLotto(**card.model_dump(), problemi=problemi, issue_urls=issue_urls)


def _gruppo_di(card: SchedaCompleta, proposal_id: str) -> Gruppo:
    """Il gruppo di cui quella proposta e' lo strumento.

    Cercato per id della tip-strumento e non per nome: due contenuti diversi
    possono parlare dello stesso strumento, e decidere «Scrapling» qui non
    deve trascinare gli usi che un altro reel ne ha proposto.
    """
    for gruppo in card.gruppi:
        if gruppo.tip is not None and gruppo.tip.id == proposal_id:
            return gruppo
    raise HTTPException(
        404, f"la proposta {proposal_id[:8]} non e' lo strumento di nessun gruppo"
    )


@router.post("/strumenti/{proposal_id}/decision", response_model=EsitoLotto)
def decidi_strumento(
    proposal_id: str, corpo: Decisione, queue: Q, registry: R, reviewer: Rev
) -> EsitoLotto:
    """Decide uno strumento, e con lui tutti i suoi utilizzi ancora aperti.

    E' la regola che rende la pagina usabile: prendere lo strumento significa
    volerlo per come lo si usa, quindi la domanda si fa UNA volta. Lo stesso
    vale al contrario — un uso di uno strumento che non si vuole non e' una
    domanda ancora aperta, e lasciarlo pendente obbligherebbe a rispondere
    «no» tante volte quanti sono gli usi di un no gia' dato.

    Chi invece vuole scegliere uso per uso non passa di qui: usa il lotto,
    che non trascina nulla.
    """
    proposal = _risolvi(queue, None, proposal_id)
    _scrittura(corpo.instance, _istanza_proposta(proposal))
    card = _scheda(queue, registry, proposal.item.source_id)
    if card is None:  # pragma: no cover - la proposta viene dal registro
        raise HTTPException(404, f"nessun contenuto con id {proposal.item.source_id}")
    gruppo = _gruppo_di(card, proposal.id)

    # Solo i pendenti: un utilizzo gia' deciso a mano porta una decisione che
    # una persona ha preso, e la cascata non la riscrive.
    da_decidere = [proposal] + [
        _risolvi(queue, proposal.item.source_id, u.id)
        for u in gruppo.utilizzi
        if u.stato == "pending"
    ]
    problemi: list[str] = []
    issue_urls: list[str] = []
    bloccate: list[AdozioneBloccata] = []
    for quale in da_decidere:
        # I progetti scelti valgono per lo strumento; ogni utilizzo va nel
        # proprio (collegarlo all'agente vive in ~/.claude, non nel repo in cui
        # si installa la libreria). Mandarli tutti nello stesso posto apriva
        # issue dove quel lavoro non si fa.
        try:
            esito = _decidi(
                reviewer, quale, corpo.verdict, corpo.reason, corpo.nota,
                corpo.repos if quale.id == proposal.id else None,
                corpo.entita,
            )
        except AdozioneBloccata as exc:
            bloccate.append(exc)
            continue
        problemi.extend(esito.problems)
        issue_urls.extend(esito.issue_urls)
    if bloccate:
        raise _bloccate_in_http(bloccate, len(da_decidere) - len(bloccate))

    aggiornata = _scheda(queue, registry, proposal.item.source_id)
    if aggiornata is None:  # pragma: no cover
        raise HTTPException(404, f"nessun contenuto con id {proposal.item.source_id}")
    return EsitoLotto(
        **aggiornata.model_dump(), problemi=problemi, issue_urls=issue_urls
    )


@router.post("/contents/{source_id:path}/strumenti", response_model=EsitoLotto)
def decidi_tutti_gli_strumenti(
    source_id: str, corpo: Decisione, queue: Q, registry: R, reviewer: Rev
) -> EsitoLotto:
    """Decide in una volta tutti gli strumenti ancora aperti di un contenuto.

    Una lista di dieci alternative non va approvata dieci volte con lo stesso
    motivo. Ogni strumento resta se stesso (propria issue, propri utilizzi
    trascinati come in `decidi_strumento`): cambia solo che la domanda si fa
    una volta. Chi ne vuole solo alcuni decide strumento per strumento.
    """
    card = _scheda(queue, registry, source_id)
    if card is None:
        raise HTTPException(404, f"nessun contenuto con id {source_id}")
    _scrittura(corpo.instance, card.instance_id)
    aperti = [g.tip.id for g in card.gruppi if g.tip and g.tip.stato == "pending"]
    if not aperti:
        raise HTTPException(409, "nessuno strumento ancora da decidere in questo contenuto")
    problemi: list[str] = []
    issue_urls: list[str] = []
    bloccate: list[HTTPException] = []
    for pid in aperti:
        try:
            esito = decidi_strumento(pid, corpo, queue, registry, reviewer)
        except HTTPException as exc:
            if exc.status_code != 422:
                raise
            bloccate.append(exc)
            continue
        problemi.extend(esito.problemi)
        issue_urls.extend(esito.issue_urls)
    if bloccate:
        raise HTTPException(422, " ".join(str(b.detail) for b in bloccate))
    aggiornata = _scheda(queue, registry, source_id)
    return EsitoLotto(**aggiornata.model_dump(), problemi=problemi, issue_urls=issue_urls)


@router.post("/contents/{source_id:path}/pacchetto", response_model=EsitoLotto)
def decidi_pacchetto(
    source_id: str, corpo: Decisione, queue: Q, registry: R, reviewer: Rev
) -> EsitoLotto:
    """Una decisione sola per un contenuto fatto di capitoli.

    Un reel che spiega una skill in quattro parti non pone quattro domande:
    pone «voglio questa skill?». La prima tip pendente porta la decisione e
    apre l'issue; le altre sono i suoi capitoli e finiscono NEL CORPO
    dell'issue come linee guida da seguire implementandola. Ricevono lo
    stesso verdetto ma nessuna issue propria (repos vuoti).
    """
    card = _scheda(queue, registry, source_id)
    if card is None:
        raise HTTPException(404, f"nessun contenuto con id {source_id}")
    _scrittura(corpo.instance, card.instance_id)
    tutte = [t for g in card.gruppi for t in ([g.tip] if g.tip else []) + g.utilizzi]
    tutte += card.pratiche
    pendenti = [t for t in tutte if t.stato == "pending"]
    if not pendenti:
        raise HTTPException(409, "nessuna tip ancora da decidere in questo contenuto")
    principale, capitoli = pendenti[0], pendenti[1:]

    nota = (corpo.nota or "").strip()
    if capitoli and corpo.verdict == "adopted":
        guida = "\n\n".join(f"### {c.titolo}\n{c.corpo}" for c in capitoli)
        nota = f"{nota}\n\n## Linee guida dai capitoli\n\n{guida}".strip()

    problemi: list[str] = []
    issue_urls: list[str] = []
    try:
        esito = _decidi(
            reviewer, _risolvi(queue, source_id, principale.id),
            corpo.verdict, corpo.reason, nota or None, corpo.repos, corpo.entita,
        )
    except AdozioneBloccata as exc:
        # I capitoli non si toccano: restano pending insieme alla principale.
        raise _bloccate_in_http([exc], 0) from exc
    problemi.extend(esito.problems)
    issue_urls.extend(esito.issue_urls)
    for c in capitoli:
        # I capitoli vivono nel corpo dell'issue della principale: adottati
        # "dentro" quella, senza una issue propria (e senza finire pending).
        _decidi(
            reviewer, _risolvi(queue, source_id, c.id), corpo.verdict,
            corpo.reason or f"capitolo di «{principale.titolo}»", None, [],
            assorbita_in=esito.issue_urls or None,
        )
    aggiornata = _scheda(queue, registry, source_id)
    return EsitoLotto(**aggiornata.model_dump(), problemi=problemi, issue_urls=issue_urls)
