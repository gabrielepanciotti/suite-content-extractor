from __future__ import annotations

from datetime import UTC, datetime

from suite_learn_core.contents import Content, InMemoryContentRegistry
from suite_learn_core.queue import InMemoryQueue
from suite_learn_core.types import Item, SourceRef

from content_extractor_backend.schede import elenco, scheda

REF = SourceRef(kind="link", source_id="instagram:ABC", url="https://x/reel/ABC/")
NODE = "contentExtractor"


def _item(title: str) -> Item:
    return Item(title=title, body="b", source_id="instagram:ABC",
                pros=["p"], cons=["c"], recommendation="adopt")


def test_the_list_groups_proposals_under_their_content():
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "telegram")
    queue.put(NODE, _item("una"))
    queue.put(NODE, _item("due"))
    (only,) = elenco(queue, registry, NODE)
    assert only.source_id == "instagram:ABC"
    assert only.quante_tip == 2
    assert only.stato == "da_vedere"


def test_a_content_with_no_proposals_still_appears():
    """Il registro e' la fonte della lista, non la coda: un contenuto che non
    ha prodotto niente e' esattamente quello che si vuole vedere."""
    registry = InMemoryContentRegistry()
    registry.record(REF, "telegram")
    (only,) = elenco(InMemoryQueue(), registry, NODE)
    assert only.stato == "fallito"


def test_the_card_carries_the_reasoning_not_just_the_verdict():
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "cli")
    queue.put(NODE, _item("una"))
    card = scheda(queue, registry, NODE, "instagram:ABC")
    assert card.tip[0].pros == ["p"]
    assert card.tip[0].cons == ["c"]


def test_an_unknown_source_returns_none_not_an_empty_card():
    assert scheda(InMemoryQueue(), InMemoryContentRegistry(), NODE, "mai") is None


def test_proposals_of_another_node_are_not_counted():
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "cli")
    queue.put("altro", _item("una"))
    (only,) = elenco(queue, registry, NODE)
    assert only.quante_tip == 0


def test_ordering_da_vedere_first_then_most_recent():
    """da_vedere galleggia in cima; a parita' di stato, il piu' recente
    (caricato decrescente) precede il piu' vecchio — non il contrario, perche'
    la pagina serve a decidere su cio' che e' appena arrivato, non a sfogliare
    un archivio dal fondo."""
    registry = InMemoryContentRegistry()
    queue = InMemoryQueue()

    # Contenuti costruiti a mano con date esplicite (record() timbra sempre
    # now()), inseriti nel registro fuori ordine per non dipendere per caso
    # dall'ordine con cui sono stati scritti.
    old_decided = Content(source_id="old-decided", origin="cli",
                           seen_at=datetime(2026, 1, 1, tzinfo=UTC))
    new_decided = Content(source_id="new-decided", origin="cli",
                           seen_at=datetime(2026, 6, 1, tzinfo=UTC))
    da_vedere = Content(source_id="pending", origin="cli",
                         seen_at=datetime(2026, 3, 1, tzinfo=UTC))
    registry._events.extend([old_decided, new_decided, da_vedere])

    old_item = Item(title="vecchia", body="b", source_id="old-decided",
                     recommendation="adopt")
    new_item = Item(title="nuova", body="b", source_id="new-decided",
                     recommendation="adopt")
    pending_item = Item(title="in attesa", body="b", source_id="pending",
                         recommendation="adopt")
    old_proposal = queue.put(NODE, old_item)
    new_proposal = queue.put(NODE, new_item)
    queue.put(NODE, pending_item)  # resta "pending" -> stato "da_vedere"
    queue.resolve(old_proposal.id, "adopted")
    queue.resolve(new_proposal.id, "adopted")

    risultato = elenco(queue, registry, NODE)
    ids = [r.source_id for r in risultato]

    assert ids[0] == "pending"
    assert ids[1:] == ["new-decided", "old-decided"]


def _strumento(title: str, tool: str) -> Item:
    return Item(title=title, body="b", source_id="instagram:ABC",
                recommendation="adopt", kind="strumento", tool=tool)


def _utilizzo(title: str, tool: str) -> Item:
    return Item(title=title, body="b", source_id="instagram:ABC",
                recommendation="adopt", kind="utilizzo", tool=tool)


def _con(*items: Item):
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "cli")
    for item in items:
        queue.put(NODE, item)
    return scheda(queue, registry, NODE, "instagram:ABC")


def test_a_tool_and_its_uses_become_one_group():
    card = _con(_strumento("Scrapling", "Scrapling"),
                _utilizzo("collegalo all'agente", "Scrapling"),
                _utilizzo("tre casi d'uso", "Scrapling"))
    (gruppo,) = card.gruppi
    assert gruppo.strumento == "Scrapling"
    assert gruppo.tip.titolo == "Scrapling"
    assert [u.titolo for u in gruppo.utilizzi] == ["collegalo all'agente",
                                                   "tre casi d'uso"]
    assert card.pratiche == []
    # La lista piatta resta la verita': i gruppi sono una vista, non altri dati.
    assert len(card.tip) == 3


def test_a_practice_belongs_to_no_group():
    card = _con(_item("una pratica"))
    assert card.gruppi == []
    assert [t.titolo for t in card.pratiche] == ["una pratica"]


def test_a_use_whose_tool_was_never_named_stays_decidable_on_its_own():
    """Non si inventa un gruppo per un uso che non dice di cosa: finirebbe da
    solo sotto uno strumento che nessuno ha proposto."""
    card = _con(Item(title="un uso orfano", body="b", source_id="instagram:ABC",
                     kind="utilizzo", tool=None))
    assert card.gruppi == []
    assert [t.titolo for t in card.pratiche] == ["un uso orfano"]


def test_a_tool_that_forgot_its_name_is_grouped_under_its_title():
    card = _con(Item(title="Usa Scrapling", body="b", source_id="instagram:ABC",
                     kind="strumento", tool=None))
    (gruppo,) = card.gruppi
    assert gruppo.strumento == "Usa Scrapling"
    assert gruppo.tip is not None


def test_uses_without_their_tool_still_form_a_group_to_decide_one_by_one():
    """Il contenuto parla di usi di qualcosa che non ha presentato: il gruppo
    esiste ma non ha nulla da adottare in blocco."""
    card = _con(_utilizzo("usalo cosi'", "Scrapling"))
    (gruppo,) = card.gruppi
    assert gruppo.tip is None
    assert len(gruppo.utilizzi) == 1


def test_one_tool_spelled_three_ways_is_still_one_group():
    card = _con(_strumento("Agent Reach", "Agent Reach"),
                _utilizzo("uno", "Agent-Reach"),
                _utilizzo("due", "agent-reach"))
    (gruppo,) = card.gruppi
    assert gruppo.strumento == "Agent Reach"
    assert len(gruppo.utilizzi) == 2


def test_una_lettura_riuscita_toglie_il_residuo_della_sola_didascalia():
    from content_extractor_backend.schede import _senza_fallimenti_superati
    from content_extractor_backend.schede import Tip

    def tip(titolo, degradato=None, stato="pending"):
        return Tip(id=titolo, titolo=titolo, corpo="c", stato=stato, pros=[], cons=[],
                   raccomandazione="adopt", degradato=degradato, tipo="pratica")

    tips = [tip("residuo", "Video non letto: x"), tip("uno"), tip("uno"), tip("due")]
    assert [t.titolo for t in _senza_fallimenti_superati(tips)] == ["uno", "due"]
