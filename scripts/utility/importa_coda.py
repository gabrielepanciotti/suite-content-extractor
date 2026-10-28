#!/usr/bin/env python3
"""Importa in questa coda la coda di un altro checkout, sotto un'istanza Life.

ContentExtractor#5 (Network #696): niente piu' code parallele. Una coda scritta
da un altro checkout (es. quello personal, fermo al 12/10) entra in quella che
il servizio legge, con ogni record etichettato `instance_id=<istanza>`.

Chiavi naturali: `source_id` per contenuti, ledger e allegati; `id` per
proposte ed esiti. Per ogni chiave della sorgente:

- non c'e' nella destinazione        -> importata (tutte le sue righe, in ordine:
                                        la coda e' append-only, l'ultima vince);
- c'e' gia' sotto la stessa istanza  -> doppione (e' il secondo giro: 0 righe);
- c'e' sotto un'altra istanza        -> conflitto: non si duplica e non si sposta,
                                        finisce nell'elenco dei conflitti.

Una proposta il cui contenuto (`item.source_id`) e' gia' di un'altra istanza e'
un conflitto anche se il suo id non c'e' piu': e' una lettura superata di quel
contenuto, e importarla la resusciterebbe sotto un'istanza sbagliata.

Prova a vuoto di default; `--esegui` scrive, dopo aver copiato ogni file
toccato in `<file>.bak-<data>-prima-import-<istanza>`. Le righe si aggiungono in
coda (append), cosi' un drain che scrive nello stesso momento non perde nulla.

Uso: backend/.venv/bin/python scripts/utility/importa_coda.py \
        --da /percorso/altra/.learn-queue --instance personal [--esegui]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RADICE / "backend"))

from content_extractor_backend import instances as ist  # noqa: E402

CODA = "contentExtractor.jsonl"
CONTENUTI = "contents.jsonl"
LEDGER = "ledger.jsonl"
ESITI = "contentExtractor.esiti.json"
CARTELLE = ("allegati", "immagini")


@dataclass
class Conteggio:
    importati: int = 0
    righe: int = 0
    doppioni: int = 0
    conflitti: list[dict] = field(default_factory=list)


def _coda() -> Path:
    return Path(os.environ.get("LEARN_QUEUE_ROOT") or RADICE / ".learn-queue")


def _righe(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for riga in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(riga)
        except ValueError:
            continue
        if isinstance(record, dict):
            out.append(record)
    return out


def _per_chiave(righe: list[dict], chiave) -> dict[str, list[dict]]:
    gruppi: dict[str, list[dict]] = defaultdict(list)
    for record in righe:
        k = chiave(record)
        if k:
            gruppi[k].append(record)
    return gruppi


def _istanze(righe: list[dict], chiave, default: str | None) -> dict[str, str]:
    """L'istanza di ogni chiave nella destinazione: quella dell'ultima riga."""
    out = {}
    for record in righe:
        k = chiave(record)
        if k:
            out[k] = record.get("instance_id") or default
    return out


def _confronta(
    sorgente: dict[str, list[dict]],
    dest: dict[str, str],
    istanza: str,
    tipo: str,
    gia_altrui=None,
) -> tuple[Conteggio, list[dict]]:
    conto, da_scrivere = Conteggio(), []
    for k, gruppo in sorgente.items():
        esistente = dest.get(k)
        if esistente == istanza:
            conto.doppioni += 1
            continue
        if esistente is None and gia_altrui:
            esistente = gia_altrui(gruppo[-1])
        if esistente is not None:
            conto.conflitti.append({"tipo": tipo, "chiave": k, "istanza_esistente": esistente})
            continue
        conto.importati += 1
        conto.righe += len(gruppo)
        da_scrivere.extend({**r, "instance_id": istanza} for r in gruppo)
    return conto, da_scrivere


def _backup(path: Path, istanza: str) -> None:
    if path.exists():
        dest = path.with_name(f"{path.name}.bak-{date.today():%Y%m%d}-prima-import-{istanza}")
        if not dest.exists():
            shutil.copy2(path, dest)


def _aggiungi(path: Path, righe: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        for record in righe:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def importa(da: Path, coda: Path, istanza: str, default: str | None, esegui: bool) -> dict:
    risultato: dict[str, Conteggio] = {}
    scritture: list[tuple[Path, list[dict]]] = []

    sid = lambda r: r.get("source_id")  # noqa: E731
    contenuti_dest = _istanze(_righe(coda / CONTENUTI), sid, default)

    def contenuto_altrui(record: dict) -> str | None:
        src = (record.get("item") or {}).get("source_id")
        altrui = contenuti_dest.get(src)
        return altrui if altrui not in (None, istanza) else None

    for nome, chiave, tipo, extra in (
        (CONTENUTI, sid, "contenuto", None),
        (LEDGER, sid, "ledger", None),
        (CODA, lambda r: r.get("id"), "proposta", contenuto_altrui),
    ):
        dest = _istanze(_righe(coda / nome), chiave, default)
        conto, righe = _confronta(_per_chiave(_righe(da / nome), chiave), dest, istanza, tipo, extra)
        risultato[nome] = conto
        if righe:
            scritture.append((coda / nome, righe))

    # Esiti: un elenco JSON, un record per id.
    esiti_src = json.loads((da / ESITI).read_text(encoding="utf-8")) if (da / ESITI).exists() else []
    esiti_dest = json.loads((coda / ESITI).read_text(encoding="utf-8")) if (coda / ESITI).exists() else []
    dest = {e["id"]: e.get("instance_id") or default for e in esiti_dest if isinstance(e, dict) and e.get("id")}
    conto, nuovi = _confronta(
        {e["id"]: [e] for e in esiti_src if isinstance(e, dict) and e.get("id")}, dest, istanza, "esito"
    )
    risultato[ESITI] = conto

    # Allegati e immagini: una cartella per contenuto (`instagram:X` -> `instagram_X`).
    importati_src = {r["source_id"] for _, rr in scritture for r in rr if r.get("source_id")}
    padrone = {s.replace(":", "_"): i for s, i in contenuti_dest.items()}
    cartelle: list[tuple[Path, Path]] = []
    for nome in CARTELLE:
        conto = Conteggio()
        for d in sorted((da / nome).iterdir()) if (da / nome).is_dir() else []:
            if not d.is_dir():
                continue
            if (coda / nome / d.name).exists():
                altrui = padrone.get(d.name)
                if altrui in (None, istanza):
                    conto.doppioni += 1
                else:
                    conto.conflitti.append({"tipo": nome, "chiave": d.name, "istanza_esistente": altrui})
            elif any(s.replace(":", "_") == d.name for s in importati_src):
                conto.importati += 1
                cartelle.append((d, coda / nome / d.name))
            else:
                conto.conflitti.append({"tipo": nome, "chiave": d.name, "istanza_esistente": "contenuto non importato"})
        risultato[nome] = conto

    if esegui:
        for path, righe in scritture:
            _backup(path, istanza)
            _aggiungi(path, righe)
        if nuovi:
            _backup(coda / ESITI, istanza)
            tmp = coda / (ESITI + ".tmp")
            tmp.write_text(json.dumps(esiti_dest + nuovi, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(tmp, coda / ESITI)
        for src, dst in cartelle:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst)

    return {
        nome: {
            "importati": c.importati,
            "righe": c.righe,
            "doppioni": c.doppioni,
            "conflitti": c.conflitti,
        }
        for nome, c in risultato.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--da", required=True, type=Path, help="la .learn-queue da importare")
    parser.add_argument("--instance", required=True)
    parser.add_argument("--esegui", action="store_true", help="scrive; senza, e' una prova a vuoto")
    parser.add_argument("--conflitti", type=Path, help="dove salvare l'elenco dei conflitti (JSON)")
    args = parser.parse_args()

    istanza = ist.per_scrittura(args.instance)
    coda = _coda()
    if args.da.resolve() == coda.resolve():
        parser.error("--da e' la coda stessa")
    if not (coda / CODA).exists():
        # Una coda vuota farebbe passare tutto per nuovo: si lancia dal checkout servito.
        parser.error(f"nessuna coda in {coda}: lancialo dal checkout servito o con LEARN_QUEUE_ROOT")
    esito = importa(args.da, coda, istanza, ist.default_id(), args.esegui)

    print(f"{'IMPORT' if args.esegui else 'PROVA A VUOTO'}: {args.da} -> {coda} come {istanza!r}")
    for nome, c in esito.items():
        print(f"  {nome}: importati {c['importati']} ({c['righe']} righe), "
              f"doppioni {c['doppioni']}, conflitti {len(c['conflitti'])}")
    conflitti = [x for c in esito.values() for x in c["conflitti"]]
    if args.conflitti:
        args.conflitti.write_text(json.dumps(conflitti, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  elenco conflitti: {args.conflitti}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
