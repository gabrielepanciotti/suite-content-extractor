from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "utility"))
from importa_coda import importa


def _jsonl(path: Path, righe: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in righe), encoding="utf-8")


def _leggi(path: Path) -> list[dict]:
    return [json.loads(r) for r in path.read_text(encoding="utf-8").splitlines() if r]


def _proposta(pid: str, src: str, status: str = "pending", **extra) -> dict:
    return {"id": pid, "node_id": "contentExtractor", "item": {"title": pid, "source_id": src},
            "status": status, "failure_reason": None, **extra}


def _scenario(tmp_path: Path) -> tuple[Path, Path]:
    da, coda = tmp_path / "da", tmp_path / "coda"
    da.mkdir(), coda.mkdir()
    # destinazione: un contenuto del lavoro, con la sua proposta (riga senza istanza = default)
    _jsonl(coda / "contents.jsonl", [{"source_id": "ig:WORK", "url": "u"}])
    _jsonl(coda / "contentExtractor.jsonl", [_proposta("p-work", "ig:WORK", instance_id="acme")])
    _jsonl(coda / "ledger.jsonl", [{"source_id": "ig:WORK", "fingerprint": "f", "instance_id": "acme"}])
    (coda / "contentExtractor.esiti.json").write_text(json.dumps([{"id": "e-work", "instance_id": "acme"}]))
    # sorgente: lo stesso contenuto (conflitto) + uno nuovo con due versioni della proposta
    _jsonl(da / "contents.jsonl", [{"source_id": "ig:WORK", "url": "u"}, {"source_id": "ig:NEW", "url": "n"}])
    _jsonl(da / "contentExtractor.jsonl", [
        _proposta("p-work", "ig:WORK"),
        _proposta("p-old", "ig:WORK"),  # superata: il suo contenuto e' gia' del lavoro
        _proposta("p-new", "ig:NEW"),
        _proposta("p-new", "ig:NEW", status="adopted"),
    ])
    _jsonl(da / "ledger.jsonl", [{"source_id": "ig:NEW", "fingerprint": "g"}])
    (da / "contentExtractor.esiti.json").write_text(json.dumps([{"id": "e-work"}, {"id": "e-new"}]))
    for nome in ("ig_NEW", "ig_WORK"):
        (da / "allegati" / nome).mkdir(parents=True)
        (da / "allegati" / nome / "lavoro.json").write_text("{}")
    return da, coda


def test_dry_run_writes_nothing(tmp_path):
    da, coda = _scenario(tmp_path)
    prima = {p.name: p.read_bytes() for p in coda.iterdir() if p.is_file()}

    esito = importa(da, coda, "personal", "acme", esegui=False)

    assert esito["contents.jsonl"]["importati"] == 1
    assert {p.name: p.read_bytes() for p in coda.iterdir() if p.is_file()} == prima
    assert not (coda / "allegati").exists()


def test_it_imports_new_keys_and_reports_the_ones_of_another_instance(tmp_path):
    da, coda = _scenario(tmp_path)

    esito = importa(da, coda, "personal", "acme", esegui=True)

    assert esito["contents.jsonl"]["importati"] == 1
    assert esito["contents.jsonl"]["conflitti"] == [
        {"tipo": "contenuto", "chiave": "ig:WORK", "istanza_esistente": "acme"}]
    assert esito["contentExtractor.jsonl"]["importati"] == 1
    assert esito["contentExtractor.jsonl"]["righe"] == 2
    assert {c["chiave"] for c in esito["contentExtractor.jsonl"]["conflitti"]} == {"p-work", "p-old"}
    assert esito["contentExtractor.esiti.json"]["importati"] == 1

    proposte = _leggi(coda / "contentExtractor.jsonl")
    assert [p["status"] for p in proposte if p["id"] == "p-new"] == ["pending", "adopted"]
    assert all(p["instance_id"] == "personal" for p in proposte if p["id"] == "p-new")
    assert [p["id"] for p in proposte].count("p-work") == 1  # non duplicata
    esiti = json.loads((coda / "contentExtractor.esiti.json").read_text())
    assert {"id": "e-new", "instance_id": "personal"} in esiti
    assert (coda / "allegati" / "ig_NEW" / "lavoro.json").exists()
    assert not (coda / "allegati" / "ig_WORK").exists()
    assert list(coda.glob("contents.jsonl.bak-*-prima-import-personal"))


def test_second_run_imports_zero(tmp_path):
    da, coda = _scenario(tmp_path)
    importa(da, coda, "personal", "acme", esegui=True)
    prima = (coda / "contentExtractor.jsonl").read_text()

    esito = importa(da, coda, "personal", "acme", esegui=True)

    assert sum(c["importati"] for c in esito.values()) == 0
    assert esito["contentExtractor.jsonl"]["doppioni"] == 1
    assert (coda / "contentExtractor.jsonl").read_text() == prima
