from __future__ import annotations

from fastapi.testclient import TestClient

from content_extractor_backend.app import app
from content_extractor_backend.api import (
    get_esiti,
    get_issue_reader,
    get_queue,
    get_registry,
    get_reviewer,
)
from suite_learn_core.esiti import Esito, FakeIssueReader, InMemoryEsitiStore, IssueInfo
from suite_learn_core.contents import InMemoryContentRegistry
from suite_learn_core.queue import InMemoryQueue, JsonlQueue
from suite_learn_core.types import Item, SourceRef

REF = SourceRef(kind="link", source_id="instagram:ABC", url="https://x/reel/ABC/")


class ReviewerFinto:
    def __init__(self, queue):
        self.queue = queue
        self.chiamate = []
        self.extra = []

    def decide(self, prefix, verdict, reason, repo=None, note=None, repos=None,
               assorbita_in=None):
        # Stessa firma del Reviewer vero: un fake piu' permissivo del reale
        # lascia passare in verde una rotta che in produzione solleva.
        self.chiamate.append((prefix, verdict, reason))
        self.extra.append((note, repos))
        from suite_learn_core.review import DecisionOutcome, find_by_prefix
        p = find_by_prefix(self.queue, prefix)
        return DecisionOutcome(proposal=self.queue.resolve(p.id, verdict))


def client_con(queue, registry, reviewer):
    app.dependency_overrides[get_queue] = lambda: queue
    app.dependency_overrides[get_registry] = lambda: registry
    app.dependency_overrides[get_reviewer] = lambda: reviewer
    return TestClient(app)


def _fixture():
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "telegram")
    a = queue.put("contentExtractor", Item(title="una", body="b", source_id="instagram:ABC"))
    b = queue.put("contentExtractor", Item(title="due", body="b", source_id="instagram:ABC"))
    return queue, registry, a, b


def test_the_list_is_served():
    queue, registry, *_ = _fixture()
    r = client_con(queue, registry, ReviewerFinto(queue)).get("/api/contents")
    assert r.status_code == 200
    assert r.json()[0]["source_id"] == "instagram:ABC"


def test_an_unknown_content_is_404():
    queue, registry, *_ = _fixture()
    r = client_con(queue, registry, ReviewerFinto(queue)).get("/api/contents/mai")
    assert r.status_code == 404


def test_deciding_one_tip_goes_through_the_reviewer():
    queue, registry, a, _ = _fixture()
    reviewer = ReviewerFinto(queue)
    r = client_con(queue, registry, reviewer).post(
        f"/api/proposals/{a.id}/decision", json={"verdict": "adopted", "reason": "serve"}
    )
    assert r.status_code == 200
    assert reviewer.chiamate == [(a.id, "adopted", "serve")]


def _giudicata(queue, raccomandazione):
    return queue.put("contentExtractor", Item(
        title="giudicata", body="b", source_id="instagram:ABC",
        recommendation=raccomandazione, verdict_reason="serve davvero",
    ))


def test_agreeing_without_a_reason_records_the_judgements_reason():
    """Riscrivere il motivo gia' sulla carta non aggiunge niente: vuoto vuol
    dire «per quel motivo», e il record lo dice con parole attribuite."""
    queue, registry, *_ = _fixture()
    p = _giudicata(queue, "adopt")
    reviewer = ReviewerFinto(queue)
    r = client_con(queue, registry, reviewer).post(
        f"/api/proposals/{p.id}/decision", json={"verdict": "adopted", "reason": "  "}
    )
    assert r.status_code == 200
    assert reviewer.chiamate == [(p.id, "adopted", "d'accordo con il giudizio: serve davvero")]


def test_going_against_the_judgement_without_a_reason_is_not_passed_off_as_agreement():
    queue, registry, *_ = _fixture()
    p = _giudicata(queue, "adopt")
    reviewer = ReviewerFinto(queue)
    client_con(queue, registry, reviewer).post(
        f"/api/proposals/{p.id}/decision", json={"verdict": "rejected"}
    )
    assert reviewer.chiamate[0][2] == "deciso contro il giudizio, senza un motivo scritto"


def test_deciding_twice_is_409_with_the_current_state():
    queue, registry, a, _ = _fixture()
    c = client_con(queue, registry, ReviewerFinto(queue))
    c.post(f"/api/proposals/{a.id}/decision", json={"verdict": "adopted", "reason": "x"})
    r = c.post(f"/api/proposals/{a.id}/decision", json={"verdict": "rejected", "reason": "y"})
    assert r.status_code == 409
    assert r.json()["detail"]["stato"] == "adopted"


def test_a_batch_leaves_untouched_tips_pending():
    queue, registry, a, b = _fixture()
    c = client_con(queue, registry, ReviewerFinto(queue))
    r = c.post("/api/contents/instagram:ABC/decision",
               json={"adotta": [a.id], "scarta": [], "reason": "prendo solo questa"})
    assert r.status_code == 200
    assert r.json()["stato"] == "parziale"
    assert [t["stato"] for t in r.json()["tip"]] == ["adopted", "pending"]


def test_a_batch_actually_rejects_through_scarta():
    queue, registry, a, b = _fixture()
    c = client_con(queue, registry, ReviewerFinto(queue))
    r = c.post("/api/contents/instagram:ABC/decision",
               json={"adotta": [], "scarta": [b.id], "reason": "non serve"})
    assert r.status_code == 200
    assert r.json()["stato"] == "parziale"
    assert [t["stato"] for t in r.json()["tip"]] == ["pending", "rejected"]


def test_an_illegal_verdict_is_422_and_never_touches_the_queue_file(tmp_path):
    queue = JsonlQueue(tmp_path)
    registry = InMemoryContentRegistry()
    a = queue.put("contentExtractor", Item(title="una", body="b", source_id="instagram:ABC"))
    path = tmp_path / "contentExtractor.jsonl"
    before = path.read_text()
    r = client_con(queue, registry, ReviewerFinto(queue)).post(
        f"/api/proposals/{a.id}/decision", json={"verdict": "adopt", "reason": "x"}
    )
    assert r.status_code == 422
    assert path.read_text() == before


def test_batch_preflight_rejects_the_whole_batch_if_one_id_is_already_decided():
    queue, registry, a, b = _fixture()
    reviewer = ReviewerFinto(queue)
    c = client_con(queue, registry, reviewer)
    c.post(f"/api/proposals/{a.id}/decision", json={"verdict": "adopted", "reason": "x"})
    reviewer.chiamate.clear()
    r = c.post("/api/contents/instagram:ABC/decision",
               json={"adotta": [b.id, a.id], "scarta": [], "reason": "lotto"})
    assert r.status_code == 409
    assert reviewer.chiamate == []
    assert {p.id: p.status for p in queue.list()}[b.id] == "pending"


def test_batch_rejects_a_tip_that_does_not_belong_to_this_content():
    queue, registry, a, b = _fixture()
    other_ref = SourceRef(kind="link", source_id="instagram:XYZ", url="https://x/reel/XYZ/")
    registry.record(other_ref, "telegram")
    other = queue.put("contentExtractor", Item(title="altra", body="b", source_id="instagram:XYZ"))
    reviewer = ReviewerFinto(queue)
    r = client_con(queue, registry, reviewer).post(
        "/api/contents/instagram:ABC/decision",
        json={"adotta": [other.id], "scarta": [], "reason": "sbagliato"},
    )
    assert r.status_code == 404
    assert reviewer.chiamate == []
    assert {p.id: p.status for p in queue.list()}[other.id] == "pending"


class ReviewerConProblemi:
    """Un Reviewer finto che decide ma segnala un artefatto non prodotto —
    come il vero Reviewer quando GhIssueCreator scrive su fallback_dir invece
    che aprire davvero un'issue.
    """

    def __init__(self, queue):
        self.queue = queue

    def decide(self, prefix, verdict, reason, repo=None, note=None, repos=None,
               assorbita_in=None):
        from suite_learn_core.review import DecisionOutcome, find_by_prefix
        p = find_by_prefix(self.queue, prefix)
        resolved = self.queue.resolve(p.id, verdict)
        return DecisionOutcome(proposal=resolved, problems=["issue non creata (gh assente)"])


def test_a_single_decision_reports_problems_the_reviewer_could_not_avoid():
    queue, registry, a, _ = _fixture()
    r = client_con(queue, registry, ReviewerConProblemi(queue)).post(
        f"/api/proposals/{a.id}/decision", json={"verdict": "adopted", "reason": "x"}
    )
    assert r.status_code == 200
    assert r.json()["problemi"] == ["issue non creata (gh assente)"]


def test_a_batch_decision_collects_problems_across_every_decision():
    queue, registry, a, b = _fixture()
    r = client_con(queue, registry, ReviewerConProblemi(queue)).post(
        "/api/contents/instagram:ABC/decision",
        json={"adotta": [a.id, b.id], "scarta": [], "reason": "x"},
    )
    assert r.status_code == 200
    assert r.json()["problemi"] == [
        "issue non creata (gh assente)", "issue non creata (gh assente)"
    ]


def _fixture_strumento():
    """Uno strumento con due usi, piu' una pratica che non c'entra."""
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "telegram")
    put = lambda i: queue.put("contentExtractor", i)
    strumento = put(Item(title="Scrapling", body="b", source_id="instagram:ABC",
                         kind="strumento", tool="Scrapling"))
    uso1 = put(Item(title="uso uno", body="b", source_id="instagram:ABC",
                    kind="utilizzo", tool="Scrapling"))
    uso2 = put(Item(title="uso due", body="b", source_id="instagram:ABC",
                    kind="utilizzo", tool="Scrapling"))
    altra = put(Item(title="pratica", body="b", source_id="instagram:ABC"))
    return queue, registry, strumento, uso1, uso2, altra


def test_adopting_a_tool_adopts_its_uses_too():
    queue, registry, strumento, uso1, uso2, altra = _fixture_strumento()
    r = client_con(queue, registry, ReviewerFinto(queue)).post(
        f"/api/strumenti/{strumento.id}/decision",
        json={"verdict": "adopted", "reason": "lo voglio"},
    )
    assert r.status_code == 200
    stati = {t["titolo"]: t["stato"] for t in r.json()["tip"]}
    assert stati == {"Scrapling": "adopted", "uso uno": "adopted",
                     "uso due": "adopted",
                     # Una pratica non e' un uso dello strumento: la cascata
                     # non la tocca, o deciderebbe cose mai chieste.
                     "pratica": "pending"}


def test_rejecting_a_tool_closes_its_uses_as_well():
    """Un uso di uno strumento che non si vuole non e' una domanda aperta."""
    queue, registry, strumento, *_ = _fixture_strumento()
    r = client_con(queue, registry, ReviewerFinto(queue)).post(
        f"/api/strumenti/{strumento.id}/decision",
        json={"verdict": "rejected", "reason": "no"},
    )
    stati = {t["titolo"]: t["stato"] for t in r.json()["tip"]}
    assert stati["Scrapling"] == "rejected"
    assert stati["uso uno"] == stati["uso due"] == "rejected"


def test_the_cascade_never_rewrites_a_use_already_decided_by_hand():
    queue, registry, strumento, uso1, uso2, _ = _fixture_strumento()
    client = client_con(queue, registry, ReviewerFinto(queue))
    client.post(f"/api/proposals/{uso1.id}/decision",
                json={"verdict": "rejected", "reason": "questo no"})
    r = client.post(f"/api/strumenti/{strumento.id}/decision",
                    json={"verdict": "adopted", "reason": "il resto si'"})
    stati = {t["titolo"]: t["stato"] for t in r.json()["tip"]}
    assert stati["uso uno"] == "rejected"
    assert stati["uso due"] == "adopted"


def test_a_use_is_not_a_tool_and_cannot_cascade():
    queue, registry, _, uso1, *_ = _fixture_strumento()
    r = client_con(queue, registry, ReviewerFinto(queue)).post(
        f"/api/strumenti/{uso1.id}/decision",
        json={"verdict": "adopted", "reason": "x"},
    )
    assert r.status_code == 404


def test_the_note_and_the_repos_reach_the_reviewer(monkeypatch):
    from content_extractor_backend import repos
    noti = (repos.Repo(nome="Offerte", slug="o/Offerte"),
            repos.Repo(nome="Cruscotto", slug="o/Cruscotto"))
    monkeypatch.setattr(repos, "conosciuti", lambda: noti)
    queue, registry, a, _ = _fixture()
    reviewer = ReviewerFinto(queue)
    client_con(queue, registry, reviewer).post(
        f"/api/proposals/{a.id}/decision",
        json={"verdict": "adopted", "reason": "ok", "nota": "cosi'",
              "repos": ["Offerte", "  ", "Cruscotto"]},
    )
    # I nomi diventano owner/repo; uno di soli spazi non e' un repo.
    assert reviewer.extra == [("cosi'", ["o/Offerte", "o/Cruscotto"])]


def test_a_judgement_that_wrote_a_sentence_opens_no_issue(monkeypatch):
    """Il giudizio aveva scritto «Life (packages/learn-core, …)» nel campo repo,
    e quel testo arrivava a `gh --repo`."""
    from content_extractor_backend import repos
    monkeypatch.setattr(repos, "conosciuti", lambda: ())
    queue, registry, *_ = _fixture()
    p = queue.put("contentExtractor", Item(
        title="x", body="b", source_id="instagram:ABC",
        target_repo="boh (una frase, non un repo)"))
    reviewer = ReviewerFinto(queue)
    client_con(queue, registry, reviewer).post(
        f"/api/proposals/{p.id}/decision", json={"verdict": "adopted"})
    assert reviewer.extra == [(None, [])]


def test_the_judged_repo_is_resolved_when_the_person_names_none(monkeypatch):
    from content_extractor_backend import repos
    monkeypatch.setattr(repos, "conosciuti",
                        lambda: (repos.Repo(nome="Life", slug="o/Life"),))
    queue, registry, *_ = _fixture()
    p = queue.put("contentExtractor", Item(
        title="x", body="b", source_id="instagram:ABC",
        target_repo="Life (packages/learn-core, non verificato)"))
    reviewer = ReviewerFinto(queue)
    client_con(queue, registry, reviewer).post(
        f"/api/proposals/{p.id}/decision", json={"verdict": "adopted"})
    assert reviewer.extra == [(None, ["o/Life"])]


def test_a_rejection_carries_no_note_because_it_opens_no_issue():
    queue, registry, a, _ = _fixture()
    reviewer = ReviewerFinto(queue)
    client_con(queue, registry, reviewer).post(
        f"/api/proposals/{a.id}/decision",
        json={"verdict": "rejected", "reason": "no", "nota": "irrilevante"},
    )
    assert reviewer.extra == [(None, None)]  # uno scarto non apre issue


def test_removing_every_project_really_opens_no_issue(monkeypatch):
    """La pagina dice «nessun progetto: non nasce nessuna issue». Con la lista
    vuota letta come «non detto», l'issue nasceva nel repo del giudizio, cioe'
    proprio quello che la persona aveva appena tolto."""
    from content_extractor_backend import repos
    monkeypatch.setattr(repos, "conosciuti",
                        lambda: (repos.Repo(nome="Life", slug="o/Life"),))
    queue, registry, *_ = _fixture()
    p = queue.put("contentExtractor", Item(
        title="x", body="b", source_id="instagram:ABC", target_repo="Life"))
    reviewer = ReviewerFinto(queue)
    client_con(queue, registry, reviewer).post(
        f"/api/proposals/{p.id}/decision",
        json={"verdict": "adopted", "repos": []})
    assert reviewer.extra == [(None, [])]


def test_a_checkout_path_resolves_to_its_repo(monkeypatch):
    """Undici giudizi hanno scritto un path ("/home/.../ContentExtractor")."""
    from content_extractor_backend import repos
    noti = (repos.Repo(nome="ContentExtractor", slug="o/ContentExtractor"),
            repos.Repo(nome="~/.claude", slug="o/.claude"))
    monkeypatch.setattr(repos, "conosciuti", lambda: noti)
    assert repos.risolvi("/nodes/personal/ContentExtractor").slug == "o/ContentExtractor"
    assert repos.risolvi("/nodes/personal/ContentExtractor/").slug == "o/ContentExtractor"
    assert repos.risolvi(r"X:\srv\ContentExtractor").slug == "o/ContentExtractor"
    assert repos.risolvi("/nodes/dev/.claude").slug == "o/.claude"
    # Un path a una cartella che non e' un repo noto resta None: mai indovinare.
    assert repos.risolvi("/nodes/dev/Life-learn-core") is None


def _client_materiale(tmp_path, lanciatore):
    """Client con la coda su disco: il materiale scrive file, non memoria."""
    from content_extractor_backend.api import get_lanciatore
    queue, registry, *_ = _fixture()
    c = client_con(queue, registry, ReviewerFinto(queue))
    app.dependency_overrides[get_lanciatore] = lambda: lanciatore
    return c, queue, registry


def test_il_materiale_riparte_agganciato_al_contenuto(tmp_path, monkeypatch):
    from content_extractor_backend import api, materiale
    monkeypatch.setenv("LEARN_QUEUE_ROOT", str(tmp_path))
    lanciatore = materiale.LanciatoreFinto()
    c, *_ = _client_materiale(tmp_path, lanciatore)

    r = c.post("/api/contents/instagram:ABC/materiale",
               data={"link": "https://drive.example/cheatsheet.pdf"})

    assert r.status_code == 200, r.text
    assert r.json()["stato"] == "in_corso"
    # Il punto di tutto: l'ingestione porta il source_id del post, altrimenti
    # le tip nuove aprirebbero una scheda scollegata.
    argv = lanciatore.avvii[0]
    assert "--allega-a" in argv
    assert argv[argv.index("--allega-a") + 1] == "instagram:ABC"
    assert "https://drive.example/cheatsheet.pdf" in argv


def test_un_materiale_senza_link_ne_file_e_rifiutato(tmp_path, monkeypatch):
    from content_extractor_backend import materiale
    monkeypatch.setenv("LEARN_QUEUE_ROOT", str(tmp_path))
    lanciatore = materiale.LanciatoreFinto()
    c, *_ = _client_materiale(tmp_path, lanciatore)

    r = c.post("/api/contents/instagram:ABC/materiale", data={})

    assert r.status_code == 422
    assert lanciatore.avvii == []


def test_un_formato_che_non_sappiamo_leggere_non_entra(tmp_path, monkeypatch):
    from content_extractor_backend import materiale
    monkeypatch.setenv("LEARN_QUEUE_ROOT", str(tmp_path))
    lanciatore = materiale.LanciatoreFinto()
    c, *_ = _client_materiale(tmp_path, lanciatore)

    r = c.post("/api/contents/instagram:ABC/materiale",
               files={"file": ("roba.zip", b"PK\x03\x04", "application/zip")})

    assert r.status_code == 422
    assert ".zip" in r.json()["detail"]
    assert lanciatore.avvii == []


def test_il_nome_del_file_non_puo_uscire_dalla_cartella(tmp_path):
    """Il nome arriva da un browser: e' testo, non un nome di file."""
    from content_extractor_backend.materiale import salva_file
    dove = salva_file(tmp_path, "instagram:ABC", "../../fuori.pdf", b"%PDF-")
    assert dove.name == "fuori.pdf"
    assert tmp_path in dove.parents


def test_la_ri_estrazione_finita_si_legge_dal_log(tmp_path):
    from content_extractor_backend.materiale import (
        Lavoro, aggiorna_da_log, cartella_allegati, scrivi_lavoro,
    )
    lavoro = Lavoro(source_id="instagram:ABC", stato="in_corso",
                    materiale="x.pdf", quando="2026-09-21T00:00:00+00:00")
    scrivi_lavoro(tmp_path, lavoro)
    log = cartella_allegati(tmp_path) / "instagram_ABC" / "ingest.log"
    log.write_text("3 proposte in coda per il nodo contentExtractor.\n")

    assert aggiorna_da_log(tmp_path, lavoro, 4).stato == "finita"


def test_una_ri_estrazione_morta_lo_dice(tmp_path):
    from content_extractor_backend.materiale import (
        Lavoro, aggiorna_da_log, cartella_allegati, scrivi_lavoro,
    )
    lavoro = Lavoro(source_id="instagram:ABC", stato="in_corso",
                    materiale="x.pdf", quando="2026-09-21T00:00:00+00:00")
    scrivi_lavoro(tmp_path, lavoro)
    log = cartella_allegati(tmp_path) / "instagram_ABC" / "ingest.log"
    log.write_text("Traceback (most recent call last):\nRuntimeError: 429\n")

    aggiornato = aggiorna_da_log(tmp_path, lavoro, 0)
    assert aggiornato.stato == "fallita"
    assert "429" in aggiornato.esito


def test_una_tip_fallita_sparisce_quando_una_lettura_dopo_ha_funzionato():
    """Il materiale mancante e' arrivato: quel fallimento non descrive piu' nulla."""
    from suite_learn_core.contents import InMemoryContentRegistry
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "telegram")
    queue.fail("contentExtractor",
               Item(title="vuota", body="", source_id="instagram:ABC"),
               "no items from instagram:ABC: refers_to_media")
    queue.put("contentExtractor",
              Item(title="dal pdf", body="b", source_id="instagram:ABC"))

    r = client_con(queue, registry, ReviewerFinto(queue)).get(
        "/api/contents/instagram:ABC")

    titoli = [t["titolo"] for t in r.json()["tip"]]
    assert titoli == ["dal pdf"]


def test_un_fallimento_con_tip_buone_va_nello_storico_non_sulla_scheda():
    from suite_learn_core.contents import InMemoryContentRegistry
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "telegram")
    queue.put("contentExtractor",
              Item(title="dalla didascalia", body="b", source_id="instagram:ABC"))
    queue.fail("contentExtractor",
               Item(title="vuota", body="", source_id="instagram:ABC"),
               "no items from instagram:ABC: refers_to_media")

    r = client_con(queue, registry, ReviewerFinto(queue)).get(
        "/api/contents/instagram:ABC")

    assert [t["titolo"] for t in r.json()["tip"]] == ["dalla didascalia"]


def test_a_package_of_chapters_is_one_decision_and_one_issue():
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "telegram")
    for t in ("capitolo uno", "capitolo due", "capitolo tre"):
        queue.put("contentExtractor", Item(title=t, body=f"corpo {t}",
                                           source_id="instagram:ABC", kind="utilizzo"))
    reviewer = ReviewerFinto(queue)
    r = client_con(queue, registry, reviewer).post(
        "/api/contents/instagram:ABC/pacchetto",
        json={"verdict": "adopted", "reason": "la voglio", "nota": "mia nota",
              "repos": []},
    )
    assert r.status_code == 200
    assert {t["stato"] for t in r.json()["tip"]} == {"adopted"}
    # Solo il primo porta la nota (con i capitoli dentro): gli altri non
    # aprono issue proprie.
    prima, *altre = reviewer.extra
    assert "mia nota" in prima[0] and "corpo capitolo due" in prima[0]
    assert all(repos == [] for _, repos in altre)


def test_lo_storico_delle_letture_elenca_ogni_esito():
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "telegram")
    registry.complete("instagram:ABC", "4 tip")
    registry.complete("instagram:ABC", "riletto, nessuna tip nuova (audio scaduto)")
    r = client_con(queue, registry, ReviewerFinto(queue)).get(
        "/api/contents/instagram:ABC/letture")
    assert [e["esito"] for e in r.json()] == [
        "4 tip", "riletto, nessuna tip nuova (audio scaduto)"]


def test_the_entity_leads_the_note_of_an_approval():
    queue, registry, a, _ = _fixture()
    reviewer = ReviewerFinto(queue)
    client_con(queue, registry, reviewer).post(
        f"/api/proposals/{a.id}/decision",
        json={"verdict": "adopted", "reason": "ok", "nota": "cosi'",
              "entita": "Life work", "repos": []},
    )
    assert reviewer.extra[0][0].startswith("**Entità Life**: Life work")


def test_the_entity_of_a_content_can_be_corrected():
    queue, registry, a, _ = _fixture()
    registry.set_entita("instagram:ABC", "Life work")
    c = client_con(queue, registry, ReviewerFinto(queue))
    assert c.get("/api/contents/instagram:ABC").json()["entita"] == "Life work"
    r = c.put("/api/contents/instagram:ABC/entita", json={"entita": "Life"})
    assert r.json()["entita"] == "Life"


def test_without_a_project_the_issue_goes_to_the_repo_of_the_entity(monkeypatch):
    from content_extractor_backend import repos
    monkeypatch.setattr(repos, "conosciuti",
                        lambda: (repos.Repo(nome="life-work", slug="o/life-work"),))
    queue, registry, a, _ = _fixture()
    reviewer = ReviewerFinto(queue)
    client_con(queue, registry, reviewer).post(
        f"/api/proposals/{a.id}/decision",
        json={"verdict": "adopted", "reason": "ok", "entita": "Life work", "repos": []},
    )
    assert reviewer.extra[0][1] == ["o/life-work"]


def test_deciding_all_the_tools_of_a_content_at_once():
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "telegram")
    for nome in ("yt-dlp", "Ollama", "n8n"):
        queue.put("contentExtractor", Item(
            title=nome, body="b", source_id="instagram:ABC",
            kind="strumento", tool=nome))
    r = client_con(queue, registry, ReviewerFinto(queue)).post(
        "/api/contents/instagram:ABC/strumenti",
        json={"verdict": "adopted", "reason": "tutti"},
    )
    assert r.status_code == 200
    assert {t["stato"] for t in r.json()["tip"]} == {"adopted"}


def test_deciding_all_the_tools_needs_one_open():
    queue, registry, *_ = _fixture()
    r = client_con(queue, registry, ReviewerFinto(queue)).post(
        "/api/contents/instagram:ABC/strumenti",
        json={"verdict": "adopted", "reason": "x"},
    )
    assert r.status_code == 409


def test_the_whole_content_with_a_tool_is_one_decision_and_one_issue():
    queue, registry, strumento, uso1, uso2, altra = _fixture_strumento()
    reviewer = ReviewerFinto(queue)
    r = client_con(queue, registry, reviewer).post(
        "/api/contents/instagram:ABC/pacchetto",
        json={"verdict": "adopted", "reason": "tutto", "repos": ["Life"]},
    )
    assert r.status_code == 200
    assert {t["stato"] for t in r.json()["tip"]} == {"adopted"}
    # La prima tip aperta e' lo strumento: e' lei che porta la decisione.
    assert reviewer.chiamate[0][0] == strumento.id


URL_ISSUE = "https://github.com/o/r/issues/69"


def _esiti_client(esiti, lettore, queue=None, registry=None):
    app.dependency_overrides[get_esiti] = lambda: esiti
    app.dependency_overrides[get_issue_reader] = lambda: lettore
    # Never the real queue: a test must not read what is on this disk.
    app.dependency_overrides[get_queue] = lambda: queue or InMemoryQueue()
    app.dependency_overrides[get_registry] = lambda: registry or InMemoryContentRegistry()
    return TestClient(app)


def test_the_register_is_served_ordered_by_state_then_tool():
    store = InMemoryEsitiStore([
        Esito(id="b", strumento="B", stato="scartato"),
        Esito(id="z", strumento="Z", stato="portato"),
        Esito(id="a", strumento="A", stato="portato"),
    ])
    r = _esiti_client(store, FakeIssueReader()).get("/api/esiti")
    assert r.status_code == 200
    assert [e["id"] for e in r.json()] == ["a", "z", "b"]


def test_an_empty_register_is_an_empty_list():
    r = _esiti_client(InMemoryEsitiStore(), FakeIssueReader()).get("/api/esiti")
    assert r.status_code == 200 and r.json() == []


def test_sync_reads_the_issues_and_returns_the_updated_list():
    store = InMemoryEsitiStore([Esito(id="s", strumento="S", issue=[URL_ISSUE])])
    lettore = FakeIssueReader({URL_ISSUE: IssueInfo(URL_ISSUE, "closed", "Stato: portato")})
    r = _esiti_client(store, lettore).post("/api/esiti/sync")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["cambiati"][0]["id"] == "s"
    assert corpo["problemi"] == []
    assert corpo["esiti"][0]["stato"] == "portato"
    assert corpo["esiti"][0]["issue_stato"] == "closed"


def test_sync_reports_an_unreadable_issue_without_failing():
    store = InMemoryEsitiStore([Esito(id="s", strumento="S", issue=[URL_ISSUE])])
    r = _esiti_client(store, FakeIssueReader({URL_ISSUE: None})).post("/api/esiti/sync")
    assert r.status_code == 200
    assert len(r.json()["problemi"]) == 1 and r.json()["cambiati"] == []


class ReviewerBloccato:
    """Come il vero quando nessuna issue nasce: la proposta resta pending."""

    def __init__(self, queue, ok=()):
        self.queue, self.ok, self.extra = queue, set(ok), []

    def decide(self, prefix, verdict, reason, repo=None, note=None, repos=None,
               assorbita_in=None):
        from suite_learn_core.review import DecisionOutcome, find_by_prefix
        p = find_by_prefix(self.queue, prefix)
        self.extra.append(assorbita_in)
        if verdict == "adopted" and p.item.title not in self.ok:
            return DecisionOutcome(proposal=p, problems=[
                "il repo o/Fantasma non esiste su GitHub",
                "adozione non registrata: la proposta resta in attesa finché "
                "non nasce almeno un'issue",
            ])
        out = DecisionOutcome(proposal=self.queue.resolve(p.id, verdict))
        if verdict == "adopted":
            out.issue_urls = [URL_ISSUE]
        return out


def test_an_adoption_with_no_issue_is_422_and_leaves_the_proposal_pending():
    queue, registry, a, _ = _fixture()
    r = client_con(queue, registry, ReviewerBloccato(queue)).post(
        f"/api/proposals/{a.id}/decision", json={"verdict": "adopted", "reason": "x"}
    )
    assert r.status_code == 422
    assert "non esiste su GitHub" in r.json()["detail"]
    assert "«una» non è stata adottata" in r.json()["detail"]
    assert queue.list(status="pending") and not queue.list(status="adopted")


def test_a_rejection_is_never_blocked():
    queue, registry, a, _ = _fixture()
    r = client_con(queue, registry, ReviewerBloccato(queue)).post(
        f"/api/proposals/{a.id}/decision", json={"verdict": "rejected", "reason": "x"}
    )
    assert r.status_code == 200


def test_a_batch_reports_the_blocked_adoption_and_keeps_the_others():
    queue, registry, a, b = _fixture()
    r = client_con(queue, registry, ReviewerBloccato(queue, ok={"due"})).post(
        "/api/contents/instagram:ABC/decision",
        json={"adotta": [a.id, b.id], "scarta": [], "reason": "x"},
    )
    assert r.status_code == 422
    assert "«una»" in r.json()["detail"] and "Le altre 1 decisioni" in r.json()["detail"]
    assert [p.item.title for p in queue.list(status="adopted")] == ["due"]
    assert [p.item.title for p in queue.list(status="pending")] == ["una"]


def test_a_blocked_package_leaves_every_chapter_pending():
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "telegram")
    for t in ("uno", "due"):
        queue.put("contentExtractor", Item(title=t, body="b", source_id="instagram:ABC",
                                           kind="utilizzo"))
    r = client_con(queue, registry, ReviewerBloccato(queue)).post(
        "/api/contents/instagram:ABC/pacchetto",
        json={"verdict": "adopted", "reason": "x", "repos": []},
    )
    assert r.status_code == 422
    assert len(queue.list(status="pending")) == 2


def test_the_chapters_of_a_package_are_adopted_into_the_main_issue():
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "telegram")
    for t in ("uno", "due"):
        queue.put("contentExtractor", Item(title=t, body="b", source_id="instagram:ABC",
                                           kind="utilizzo"))
    reviewer = ReviewerBloccato(queue, ok={"uno", "due"})
    r = client_con(queue, registry, reviewer).post(
        "/api/contents/instagram:ABC/pacchetto",
        json={"verdict": "adopted", "reason": "x", "repos": []},
    )
    assert r.status_code == 200
    assert reviewer.extra == [None, [URL_ISSUE]]
    assert len(queue.list(status="adopted")) == 2


def test_repos_marks_the_ones_github_does_not_know(monkeypatch):
    from content_extractor_backend import api
    from content_extractor_backend.repos import Repo
    monkeypatch.setattr(api, "conosciuti", lambda: (
        Repo(nome="Vero", slug="o/Vero"), Repo(nome="Fantasma", slug="o/Fantasma")))

    class Finto:
        def exists(self, repo):
            return repo == "o/Vero"

    app.dependency_overrides[api.get_repo_checker] = lambda: Finto()
    r = TestClient(app).get("/api/repos")
    by = {x["nome"]: x for x in r.json()}
    assert by["Vero"]["esiste"] is True and by["Vero"]["motivo"] is None
    assert by["Fantasma"]["esiste"] is False
    assert by["Fantasma"]["motivo"] == "il repo o/Fantasma non esiste su GitHub"


def test_anomalies_are_served(tmp_path, monkeypatch):
    from content_extractor_backend import api
    monkeypatch.setenv("LEARN_QUEUE_ROOT", str(tmp_path))
    queue = InMemoryQueue()
    p = queue.put("contentExtractor", Item(title="t", body="b", source_id="x"))
    queue.resolve(p.id, "adopted")
    store = InMemoryEsitiStore([Esito(id="c", strumento="C", issue=[URL_ISSUE],
                                      issue_stato="closed", stato="aperto")])
    r = _esiti_client(store, FakeIssueReader(), queue).get("/api/esiti/anomalie")
    assert r.status_code == 200
    assert {a["tipo"] for a in r.json()} == {"adottata_senza_issue", "chiusa_senza_esito"}


def test_no_anomalies_is_an_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("LEARN_QUEUE_ROOT", str(tmp_path))
    r = _esiti_client(InMemoryEsitiStore(), FakeIssueReader()).get("/api/esiti/anomalie")
    assert r.status_code == 200 and r.json() == []


def test_the_register_carries_the_content_each_tool_came_from():
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.record(REF, "telegram")
    registry.complete("instagram:ABC", "ok", fonte="link https://x.test/cheat")
    p = queue.put("contentExtractor", Item(title="Tip", body="corpo", source_id="instagram:ABC"))
    store = InMemoryEsitiStore([Esito(id="s", strumento="S", proposte=[p.id],
                                      fonti=["instagram:ABC"])])
    r = _esiti_client(store, FakeIssueReader(), queue, registry).get("/api/esiti")
    [fonte] = r.json()[0]["contenuto"]
    assert fonte["url"] == "https://x/reel/ABC/"
    assert fonte["tips"] == [{"id": p.id, "title": "Tip", "body": "corpo"}]
    assert fonte["aggiunti"][0]["tipo"] == "link"


def test_the_register_serves_the_guide():
    store = InMemoryEsitiStore([Esito(id="s", strumento="S", guida="## Uso\n- passo")])
    [e] = _esiti_client(store, FakeIssueReader()).get("/api/esiti").json()
    assert e["guida"] == "## Uso\n- passo"


def test_the_register_serves_the_card_of_each_tool():
    store = InMemoryEsitiStore([Esito(
        id="w", strumento="Whisper", categoria="ingest", costo="gratis",
        nodi=["Life"], a_cosa_serve="trascrive", problema="reel senza testo",
        funzionalita=["locale"], passi=["salva", "ingerisci"],
        idea_originale="alternative self-hosted", implementazione="video-understand",
    )])
    [e] = _esiti_client(store, FakeIssueReader()).get("/api/esiti").json()
    assert e["categoria"] == "ingest" and e["costo"] == "gratis"
    assert e["passi"] == ["salva", "ingerisci"] and e["nodi"] == ["Life"]
    assert e["idea_originale"] == "alternative self-hosted"


def test_sync_brings_in_the_card_written_on_the_issue():
    store = InMemoryEsitiStore([Esito(id="s", strumento="S", issue=[URL_ISSUE])])
    card = "Scheda: s\n\nCategoria: modelli\nCosto: api\nA cosa serve: un gateway"
    lettore = FakeIssueReader({URL_ISSUE: IssueInfo(URL_ISSUE, "open", card, comments=(card,))})
    corpo = _esiti_client(store, lettore).post("/api/esiti/sync").json()
    [e] = corpo["esiti"]
    assert e["categoria"] == "modelli" and e["costo"] == "api" and e["stato"] == "aperto"
