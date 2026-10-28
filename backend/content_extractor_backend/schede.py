"""Dai file alla scheda, senza toccare HTTP.

Sta separato dalle rotte perche' e' la parte che vale la pena testare: le rotte
sono cablaggio, questo e' il significato. La lista nasce dal REGISTRO, non dalla
coda — un contenuto che non ha prodotto nemmeno una tip e' proprio quello che si
vuole vedere, e partendo dalla coda sparirebbe.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from suite_learn_core.promessa import promette_contenuto
from suite_learn_core.contents import Content, ContentRegistry
from suite_learn_core.pipeline import MOTIVI_GATE
from suite_learn_core.queue import Proposal, ProposalQueue
from .permalink import canonico
from .repos import risolvi
from suite_learn_core.tool_state import LABELS, ToolState, tool_state


class Tip(BaseModel):
    id: str
    titolo: str
    corpo: str
    stato: str
    pros: list[str]
    cons: list[str]
    raccomandazione: str
    approfondimento: str | None = None
    degradato: str | None = None
    impatto: int | None = None
    """Stima 1-5 del giudice sull'effetto nei sistemi dell'utente."""
    nota_giudizio: str | None = None
    motivo_verdetto: str | None = None
    """Perche' il verdetto e' quello, in una riga.

    Distinto da `nota_giudizio`, che dice un'altra cosa — che il giudizio e'
    stato dato con un contesto incompleto. E' il campo su cui si decide: senza,
    la scheda mostra un verdetto e nessun motivo per crederci.
    """
    repo: str | None = None
    motivo_fallimento: str | None = None
    """Perche' l'estrazione non ha prodotto niente, in italiano.

    La coda registra i codici del gate (`refers_to_media`, `no_items`…) perche'
    il gate si tara su quelli; qui si legge una persona, e «refers_to_media» non
    dice a nessuno che il contenuto sta nel video e non nella didascalia.
    """
    repo_suggerito: str | None = None
    """Il nome del repo che il giudizio indica, se corrisponde a uno vero.

    `repo` resta il testo del giudizio, che puo' essere una frase; questo e'
    cio' che la pagina propone come scelta, e None quando non c'e' niente di
    proponibile — meglio un campo vuoto che un'issue aperta nel posto sbagliato.
    """
    tipo: str = "pratica"
    """strumento | utilizzo | pratica. Decide COME si decide, non solo cosa."""
    strumento: str | None = None
    """Il nome dello strumento a cui appartiene: la chiave del gruppo."""


class Gruppo(BaseModel):
    """Uno strumento e i modi di usarlo, come si decidono: insieme.

    Esiste perche' la domanda «lo voglio?» si fa una volta sullo strumento e
    non una volta per utilizzo: prendere lo strumento implica prenderne gli
    usi, e una lista piatta ripete la stessa domanda cinque volte senza mai
    offrire il modo di rispondere una volta sola.
    """

    strumento: str
    tip: Tip | None = None
    """La tip che E' lo strumento. None quando il contenuto descrive solo modi
    di usare qualcosa che non ha presentato: il gruppo resta, e gli utilizzi
    si decidono uno per uno, perche' non c'e' niente da adottare in blocco."""
    utilizzi: list[Tip] = []


class Sintesi(BaseModel):
    source_id: str
    titolo: str | None
    url: str | None
    url_canonico: str | None = None
    """L'indirizzo che apre QUESTO post, non il lettore di reel. Vedi permalink.py."""
    origine: str
    caricato: str
    data_approssimata: bool
    stato: ToolState
    stato_etichetta: str
    quante_tip: int
    esito: str | None
    entita: str | None = None
    instance_id: str | None = None
    """L'istanza Life del contenuto (ContentExtractor#4): il badge nella vista «tutte»."""
    manca_allegato: bool = False
    """Il post promette un contenuto dietro un'azione: sta anche nell'elenco,
    perche' e' li' che si sceglie su cosa tornare."""
    impatto: int | None = None
    """La stima migliore fra le tip del contenuto: e' cio' che ordina l'elenco."""
    consigliato: str | None = None
    """Cosa dice il giudizio: «si» se consiglia tutte le tip, «no» se le sconsiglia
    tutte, «misto» se divide; None se nessuna ha un giudizio."""
    materiale_aggiunto: bool = False
    """Una fonte aggiunta e' stata letta: la promessa del post non e' piu' un buco."""
    in_rielaborazione: bool = False
    """Una fonte aggiunta e' in corso di lettura (lo imposta l'API, che sa dei lavori)."""


class SchedaCompleta(Sintesi):
    tip: list[Tip]
    """Tutte le tip in fila, nell'ordine della coda. Resta la verita' piatta:
    `gruppi` e `pratiche` sono due viste della stessa lista, non altri dati."""
    gruppi: list[Gruppo] = []
    pratiche: list[Tip] = []
    """Le tip che non appartengono a nessuno strumento: si decidono da sole."""
    entita: str | None = None
    """Il post promette un file dietro un'azione (commenta, scrivimi, link in bio).

    E' l'unico caso in cui serve una persona: nessun motore puo' commentare al
    posto tuo. Tenuto distinto da `da_leggere_immagini` apposta — un carosello
    non chiede niente a nessuno, e chiedere un'azione per averlo mandava a fare
    un giro a vuoto (successo davvero, su instagram:DbdQgnqTtFx).
    """
    da_leggere_immagini: bool = False
    """Il contenuto sta nelle slide e il livello 2 sa leggere solo l'audio.

    Non e' lavoro dell'utente: e' una nostra capacita' che manca, e la pagina
    lo dice cosi' invece di far credere che manchi qualcosa a lui.
    """


def _motivo_fallimento(reason: str | None) -> str | None:
    """Il motivo del fallimento come lo legge una persona.

    La riga registrata e' «no items from <fonte>: refers_to_media, no_items,
    self_reported»: la fonte e' gia' il titolo della scheda, e i codici sono
    il vocabolario del gate. Si tengono solo i codici, tradotti; uno
    sconosciuto passa com'e', perche' un codice nuovo e' un'informazione e
    nasconderlo lascerebbe la scheda a dire «fallita» senza dire altro.
    """
    if not reason:
        return None
    coda = reason.rsplit(":", 1)[-1]
    codici = [c.strip() for c in coda.split(",") if c.strip()]
    if not codici:
        return reason
    return ", ".join(MOTIVI_GATE.get(c, c) for c in codici)


def _tip(p: Proposal) -> Tip:
    return Tip(
        id=p.id,
        titolo=_titolo_tip(p), corpo=p.item.body, stato=p.status,
        pros=p.item.pros, cons=p.item.cons,
        raccomandazione=p.item.recommendation,
        approfondimento=p.item.expansion,
        degradato=_pulisci_degradato(p.item.degraded_reason),
        impatto=p.item.impact,
        nota_giudizio=p.item.judgement_note,
        motivo_verdetto=p.item.verdict_reason,
        repo=p.item.target_repo,
        motivo_fallimento=_motivo_fallimento(p.failure_reason),
        repo_suggerito=(r.nome if (r := risolvi(p.item.target_repo)) else None),
        tipo=p.item.kind,
        strumento=_chiave_strumento(p.item),
    )


_SOCIAL = (
    "instagram.com", "tiktok.com", "facebook.com", "threads.net",
    "x.com", "twitter.com", "youtube.com", "youtu.be",
)


def _e_post(url: str | None) -> bool:
    """Se la fonte e' un post social, cioe' se queste due etichette hanno senso.

    Serve contro un falso positivo vero: il README di Agent-Reach su GitHub
    risultava insieme «chiede un'azione» (la parola "send" nel testo) e «da
    leggere nelle immagini» (il livello 2 dice «nessun contenuto multimediale»,
    che su un README e' semplicemente la verita'). Una pagina di documentazione
    non promette niente a nessuno e non ha slide da leggere.
    """
    return bool(url) and any(d in url for d in _SOCIAL)


def _manca_allegato(tips: list[Tip]) -> bool:
    """Il post promette un file dietro un'azione da fare a mano.

    Si legge in cio' che il giudizio ha gia' scritto — corpo e contro della
    tip — perche' la didascalia grezza non viene conservata da nessuna parte:
    il registro tiene il link, non il testo. Due condizioni insieme, non una:
    con la sola promessa ("commenta") ogni post che invita a commentare
    chiedeva all'utente un'azione inutile.
    """
    for tip in tips:
        if promette_contenuto(" ".join([tip.corpo, *tip.cons, *tip.pros])):
            return True
    return False


def _da_leggere_immagini(tips: list[Tip]) -> bool:
    """Il livello 2 si e' fermato perche' non c'era audio da ascoltare."""
    for tip in tips:
        testo = f"{tip.degradato or ''} {tip.motivo_fallimento or ''}".lower()
        if "multimediale" in testo or "no media" in testo or "rimanda al video" in testo:
            return True
    return False


def _senza_fallimenti_superati(tips: list[Tip]) -> list[Tip]:
    """Toglie le tip fallite a cui una lettura successiva ha posto rimedio.

    Quando il materiale mancante arriva e l'estrazione riparte, il fallimento
    di prima non descrive piu' niente: e' la cronaca di un tentativo, non lo
    stato del contenuto. Lasciarlo lascerebbe sulla scheda «non estratta:
    rimanda al video» accanto alle tip appena estratte da quel video.

    Si guarda la POSIZIONE, non un orario: la coda e' un file append-only,
    quindi cio' che viene dopo nel file e' venuto dopo nel tempo. Una tip
    fallita sopravvive se dopo di lei non c'e' altro — la' il fallimento e'
    ancora l'unica cosa vera che si sa del contenuto.

    La riga nella coda resta: sparisce dalla scheda, non dal registro.
    """
    # Con almeno una tip buona la scheda non mostra i fallimenti: una lettura
    # che non ha trovato niente di nuovo non e' stato del contenuto. Restano
    # nello storico delle letture, che si apre a parte.
    if any(t.stato != "failed" for t in tips):
        tips = [t for t in tips if t.stato != "failed"]
    # Una lettura riuscita (media o immagini) sostituisce quella fatta sulla
    # sola didascalia: la tip che porta ancora «video non letto» e' il residuo
    # del primo tentativo, e lasciarla fa dire alla scheda che le slide non
    # sono state lette quando le tip accanto vengono proprio da li'.
    if any(t.degradato is None for t in tips):
        # Una gia' decisa da una persona resta: e' una decisione, non un residuo.
        tips = [t for t in tips if t.degradato is None or t.stato != "pending"]
    return _senza_doppioni(tips)


def _senza_doppioni(tips: list[Tip]) -> list[Tip]:
    """Lo stesso titolo letto due volte e' una tip sola.

    Resta quella gia' decisa da una persona, se c'e'; altrimenti l'ultima
    arrivata. L'ordine della coda si conserva.
    """
    scelto: dict[tuple[str, str], Tip] = {}
    for t in tips:
        chiave = (t.tipo, " ".join(t.titolo.lower().split()))
        corrente = scelto.get(chiave)
        if corrente is None or corrente.stato == "pending" or t.stato != "pending":
            scelto[chiave] = t
    visti: set[int] = set()
    out = []
    for t in tips:
        if any(t is v for v in scelto.values()) and id(t) not in visti:
            visti.add(id(t))
            out.append(t)
    return out


def _chiave_strumento(item) -> str | None:
    """Il nome dello strumento di un item, o None se non ne ha uno.

    Uno `strumento` senza nome prende il proprio titolo: il giudizio lo ha
    riconosciuto come strumento e non gli ha dato un nome, e perdere il gruppo
    per un campo vuoto sarebbe peggio che chiamarlo come si chiama la tip. Un
    `utilizzo` senza nome invece NON si inventa un gruppo: un uso che non dice
    di cosa non e' raggruppabile con niente, e finisce fra le pratiche.
    """
    if item.kind == "strumento":
        return item.tool or item.title
    if item.kind == "utilizzo":
        return item.tool
    return None


def _piega(nome: str) -> str:
    return "".join(c for c in nome.casefold() if c.isalnum())


def _raggruppa(tips: list[Tip]) -> tuple[list[Gruppo], list[Tip]]:
    """Le stesse tip viste come gruppi + pratiche sciolte.

    L'ordine dei gruppi e' quello di prima apparizione nella coda, e dentro
    ogni gruppo lo strumento viene prima dei suoi usi: e' l'ordine in cui si
    decide — prima «lo voglio?», poi «per fare cosa?».
    """
    gruppi: dict[str, Gruppo] = {}
    pratiche: list[Tip] = []
    for tip in tips:
        if tip.strumento is None:
            pratiche.append(tip)
            continue
        # Folded, because the judge sees one item at a time and spells the same
        # tool three ways ("Agent Reach", "Agent-Reach", "agent-reach"): taken
        # literally, one tool became three groups, each asking the question
        # the grouping exists to ask once. The first spelling is the one shown.
        chiave = _piega(tip.strumento)
        gruppo = gruppi.setdefault(
            chiave, Gruppo(strumento=tip.strumento, utilizzi=[])
        )
        if tip.tipo == "strumento" and gruppo.tip is None:
            gruppo.tip = tip
        else:
            # Un secondo `strumento` con la stessa chiave non si perde: cade
            # fra gli utilizzi, dove resta decidibile. Scartarlo in silenzio
            # toglierebbe dalla pagina una tip che la coda contiene.
            gruppo.utilizzi.append(tip)
    # Un contenuto presenta di norma UNA cosa. Il giudice vede una tip alla
    # volta e puo' battezzare lo stesso soggetto con due nomi («Claude Code» e
    # «/retro»): i gruppi senza la propria tip-strumento, se ce n'e' uno solo
    # che la ha, ne sono usi — chiedere quattro volte «lo voglio?» sullo
    # stesso post non ha senso.
    con_tip = [g for g in gruppi.values() if g.tip is not None]
    if len(con_tip) == 1:
        principale = con_tip[0]
        for g in list(gruppi.values()):
            if g is not principale and g.tip is None:
                principale.utilizzi.extend(g.utilizzi)
                del gruppi[_piega(g.strumento)]
    return list(gruppi.values()), pratiche


_MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]


def _titolo_tip(p: Proposal) -> str:
    """Una lettura fallita porta l'id della fonte come titolo: non si mostra."""
    if p.status == "failed" and p.item.title == p.item.source_id:
        return "Una lettura non è andata a buon fine"
    return p.item.title


def _pulisci_degradato(motivo: str | None) -> str | None:
    """Le righe gia' in coda portano ancora la riga di comando: le riscrive."""
    if motivo and ("Command '[" in motivo or motivo.startswith(("instagram:", "youtube:"))):
        from suite_learn_core.pipeline import _spiega_media

        return _spiega_media(Exception(motivo))
    return motivo


def _titolo_leggibile(content: Content, proposals: list[Proposal]) -> str:
    """Un titolo che dice di cosa si parla, mai l'id grezzo della fonte.

    Ordine: il titolo vero se c'e'; altrimenti lo strumento di cui parlano le
    tip; altrimenti «Post Instagram del 6 ott». `instagram:DeH-fy3k4dG` non
    dice niente a chi guarda la lista.
    """
    if content.title and content.title != content.source_id:
        return content.title
    buone = [p for p in proposals if p.status != "failed"]
    if buone:
        # Il titolo della prima tip dice di cosa parla il contenuto; il nome
        # dello strumento da solo («Claude Code») e' l'ospite, non il tema.
        return buone[0].item.title
    prefisso = content.source_id.split(":", 1)[0]
    nome = {"instagram": "Post Instagram", "youtube": "Video YouTube"}.get(prefisso, "Contenuto")
    d = content.seen_at
    return f"{nome} del {d.day} {_MESI[d.month - 1]}"


def _consigliato(proposals: list[Proposal]) -> str | None:
    """Il parere del giudizio su tutto il contenuto, in una parola."""
    pareri = {
        p.item.recommendation for p in proposals
        if p.status != "failed" and p.item.recommendation in ("adopt", "skip")
    }
    if pareri == {"adopt"}:
        return "si"
    if pareri == {"skip"}:
        return "no"
    return "misto" if pareri else None


def _sintesi(
    content: Content, proposals: list[Proposal], default_instance: str | None = None
) -> Sintesi:
    stato = tool_state(proposals)
    return Sintesi(
        source_id=content.source_id, titolo=_titolo_leggibile(content, proposals), url=content.url,
        url_canonico=canonico(content.url),
        origine=content.origin, caricato=content.seen_at.isoformat(),
        data_approssimata=content.seen_at_approximate,
        stato=stato, stato_etichetta=LABELS[stato],
        quante_tip=len([p for p in proposals if p.status != "failed"]),
        esito=content.outcome,
        entita=content.entita,
        # Le righe anteriori al contratto non la portano: sono del default del device.
        instance_id=content.instance_id or default_instance,
        consigliato=_consigliato(proposals),
        impatto=max(
            (p.item.impact for p in proposals
             if p.status != "failed" and p.item.impact), default=None,
        ),
        manca_allegato=_e_post(content.url)
        and (content.richiede_azione or _manca_allegato([_tip(p) for p in proposals])),
    )


def _by_source(queue: ProposalQueue, node_id: str) -> dict[str, list[Proposal]]:
    grouped: dict[str, list[Proposal]] = {}
    for p in queue.list(node_id=node_id):
        grouped.setdefault(p.item.source_id, []).append(p)
    return grouped


def elenco(
    queue: ProposalQueue, registry: ContentRegistry, node_id: str,
    default_instance: str | None = None, instance: str | None = None,
) -> list[Sintesi]:
    """I contenuti, di una sola istanza o (instance None) di tutte."""
    grouped = _by_source(queue, node_id)
    schede = [
        _sintesi(c, grouped.get(c.source_id, []), default_instance) for c in registry.list()
    ]
    if instance is not None:
        schede = [s for s in schede if s.instance_id == instance]
    # Da decidere in cima, poi per data DECRESCENTE (il piu' recente prima):
    # la pagina serve a decidere su cio' che e' appena arrivato, non a
    # sfogliare un archivio dal fondo. Due passate che sfruttano l'ordinamento
    # stabile di Python: prima per data decrescente (caricato e' ISO 8601,
    # quindi ordina lessicograficamente come cronologicamente), poi per stato
    # — la seconda passata non tocca l'ordine per data gia' raggiunto entro
    # ogni gruppo di stato.
    schede.sort(key=lambda s: s.caricato, reverse=True)
    schede.sort(key=lambda s: s.stato != "da_vedere")
    return schede


def scheda(
    queue: ProposalQueue, registry: ContentRegistry, node_id: str, source_id: str,
    default_instance: str | None = None,
) -> SchedaCompleta | None:
    content = next(
        (c for c in registry.list() if c.source_id == source_id), None
    )
    if content is None:
        return None
    proposals = _by_source(queue, node_id).get(source_id, [])
    tips = _senza_fallimenti_superati([_tip(p) for p in proposals])
    gruppi, pratiche = _raggruppa(tips)
    return SchedaCompleta(
        **_sintesi(content, proposals, default_instance).model_dump(),
        tip=tips, gruppi=gruppi, pratiche=pratiche,
        da_leggere_immagini=_e_post(content.url) and _da_leggere_immagini(tips),
    )
