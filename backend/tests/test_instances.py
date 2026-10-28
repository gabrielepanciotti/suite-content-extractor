"""Il contratto operatore (ContentExtractor#4, spec Life 2026-10-14 §4) sull'API."""
from __future__ import annotations

from fastapi.testclient import TestClient

from content_extractor_backend.api import get_queue, get_registry, get_reviewer
from content_extractor_backend.app import app
from suite_learn_core.contents import Content, InMemoryContentRegistry
from suite_learn_core.queue import InMemoryQueue
from suite_learn_core.types import Item

from test_api import ReviewerFinto


def _client():
    queue, registry = InMemoryQueue(), InMemoryContentRegistry()
    registry.append(Content(source_id="s:alfa", origin="telegram", instance_id="alfa"))
    registry.append(Content(source_id="s:beta", origin="telegram", instance_id="beta"))
    # Riga anteriore al contratto: senza istanza, vale il default del device.
    registry.append(Content(source_id="s:vecchio", origin="telegram"))
    pa = InMemoryQueue.put(queue, "contentExtractor", Item(title="a", body="b", source_id="s:alfa"))
    queue._items[pa.id] = pa.model_copy(update={"instance_id": "alfa"})
    pb = queue.put("contentExtractor", Item(title="b", body="b", source_id="s:beta"))
    queue._items[pb.id] = pb.model_copy(update={"instance_id": "beta"})
    app.dependency_overrides[get_queue] = lambda: queue
    app.dependency_overrides[get_registry] = lambda: registry
    app.dependency_overrides[get_reviewer] = lambda: ReviewerFinto(queue)
    return TestClient(app), pa, pb


def test_instances_lists_every_one_and_names_the_unreachable():
    client, *_ = _client()
    r = client.get("/api/instances")
    assert r.status_code == 200
    per_id = {i["id"]: i for i in r.json()}
    assert per_id["alfa"]["status"] == "ok" and per_id["alfa"]["default"] is True
    assert per_id["alfa"]["channels"]["telegram_chat_id"] == -100123
    assert per_id["alfa"]["channels"]["bus_tenant"] == "alfa"
    # Irraggiungibile: c'e', con il motivo — non sparisce.
    assert per_id["beta"]["status"] == "unreachable"
    assert "path assente" in per_id["beta"]["reason"]


def test_read_without_instance_returns_all_with_badge():
    client, *_ = _client()
    righe = client.get("/api/contents").json()
    assert {(r["source_id"], r["instance_id"]) for r in righe} == {
        ("s:alfa", "alfa"), ("s:beta", "beta"), ("s:vecchio", "alfa"),
    }


def test_read_filtered_by_instance():
    client, *_ = _client()
    righe = client.get("/api/contents", params={"instance": "beta"}).json()
    assert [r["source_id"] for r in righe] == ["s:beta"]


def test_unknown_instance_is_422_with_the_valid_ids():
    client, *_ = _client()
    r = client.get("/api/contents", params={"instance": "gamma"})
    assert r.status_code == 422
    assert r.json()["detail"]["valid"] == ["alfa", "beta"]


def test_write_with_unknown_instance_is_422():
    client, pa, _ = _client()
    r = client.post(f"/api/proposals/{pa.id}/decision",
                    json={"verdict": "rejected", "instance": "gamma"})
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "instance_unknown"


def test_write_on_a_record_of_another_instance_is_422():
    client, pa, _ = _client()
    r = client.post(f"/api/proposals/{pa.id}/decision",
                    json={"verdict": "rejected", "instance": "beta"})
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "instance_mismatch"


def test_write_without_instance_uses_the_record_one():
    client, _, pb = _client()
    r = client.post(f"/api/proposals/{pb.id}/decision", json={"verdict": "rejected"})
    assert r.status_code == 200
