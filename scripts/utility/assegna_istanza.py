#!/usr/bin/env python3
"""Rietichetta con la loro istanza Life i record scritti prima del contratto operatore.

ContentExtractor#4, spec Life 2026-10-14 §4.2: ogni record porta `instance_id`.
Migrazione additiva: si aggiunge il campo dove manca, nient'altro cambia e
nessuna riga sparisce (una riga illeggibile resta com'e'). Prima di scrivere si
copia ogni file in `<file>.bak-<data>-prima-istanza`.

L'istanza e' quella che li ha prodotti: il deploy che ha scritto questa coda.
Non si scrive a mano: senza `--instance` vale il default del device, letto dal
registro con il lettore di Life (lo Scheduler ha dovuto rietichettare 16 record
per un `personal` scritto a mano).

Uso: backend/.venv/bin/python scripts/utility/assegna_istanza.py [--instance ID] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RADICE / "backend"))

from content_extractor_backend import instances as ist  # noqa: E402


def _coda() -> Path:
    return Path(os.environ.get("LEARN_QUEUE_ROOT") or RADICE / ".learn-queue")


def _jsonl(path: Path, istanza: str) -> tuple[list[str], int]:
    righe, cambiate = [], 0
    for riga in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(riga)
        except ValueError:
            righe.append(riga)
            continue
        if isinstance(record, dict) and not record.get("instance_id"):
            record["instance_id"] = istanza
            riga = json.dumps(record, ensure_ascii=False)
            cambiate += 1
        righe.append(riga)
    return righe, cambiate


def _scrivi(path: Path, testo: str) -> None:
    shutil.copy2(path, path.with_name(f"{path.name}.bak-{date.today():%Y%m%d}-prima-istanza"))
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(testo, encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    istanza = ist.per_scrittura(args.instance)
    coda = _coda()
    print(f"Istanza: {istanza} — coda: {coda}")

    for path in sorted(coda.glob("*.jsonl")):
        righe, cambiate = _jsonl(path, istanza)
        print(f"{path.name}: {cambiate} righe su {len(righe)}")
        if cambiate and not args.dry_run:
            _scrivi(path, "\n".join(righe) + "\n")

    for path in sorted(coda.glob("*.esiti.json")):
        esiti = json.loads(path.read_text(encoding="utf-8"))
        cambiati = 0
        for esito in esiti if isinstance(esiti, list) else []:
            if isinstance(esito, dict) and not esito.get("instance_id"):
                esito["instance_id"] = istanza
                cambiati += 1
        print(f"{path.name}: {cambiati} esiti")
        if cambiati and not args.dry_run:
            _scrivi(path, json.dumps(esiti, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
