"""Traduce in italiano le proposte gia' in coda, senza rileggere le fonti.

One-off: dal 16/09 la pipeline scrive gia' in italiano (learn-core/lingua.py),
ma le proposte nate prima sono meta' in inglese. Rileggere le fonti costerebbe
video e trascrizioni gia' pagati; qui si riscrive solo il testo, con
`queue.replace`, che per costruzione non tocca lo stato — una traduzione non e'
una decisione.

Riprendibile: una proposta gia' tradotta e' riconosciuta dal modello, che la
restituisce identica, e il confronto la salta senza riscriverla.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from suite_backend_core.cli_llm import build_llm
from suite_learn_core.parsing import loads_object
from suite_learn_core.queue import JsonlQueue

CODA = Path(__file__).resolve().parents[2] / ".learn-queue"
CAMPI_TESTO = ("title", "body", "expansion", "verdict_reason", "judgement_note", "degraded_reason")
CAMPI_LISTA = ("pros", "cons")

SYSTEM = (
    "Translate the JSON values you receive into Italian. Answer with JSON only, "
    "with exactly the same keys. A value already in Italian comes back unchanged. "
    "Keep product names, commands, code, URLs and identifiers as they are. "
    "null stays null; lists keep their length and order."
)


def main() -> int:
    queue = JsonlQueue(CODA)
    # With AI_BACKEND=llm-run the instance router picks the model (service contentExtractor.traduzione); other backends ignore the name.
    llm = build_llm(servizio="contentExtractor.traduzione")
    proposte = [p for p in queue.list() if p.status != "failed"]
    if len(sys.argv) > 1:
        # `--solo <prefisso-titolo>`: una prova su una proposta prima del giro intero.
        proposte = [p for p in proposte if p.item.title.startswith(sys.argv[-1])]
    cambiate = 0
    for i, proposta in enumerate(proposte, 1):
        item = proposta.item
        testo = {k: getattr(item, k) for k in CAMPI_TESTO + CAMPI_LISTA}
        try:
            risposta = loads_object(
                llm.complete(json.dumps(testo, ensure_ascii=False), system=SYSTEM)
            )
        except Exception as exc:  # noqa: BLE001 - one failure must not stop the rest
            print(f"[{i}/{len(proposte)}] {proposta.id[:8]} non tradotta: {exc}", flush=True)
            continue
        aggiornamento = {}
        for k in CAMPI_TESTO:
            v = risposta.get(k)
            # Only a string replaces a string: a missing or malformed answer
            # keeps the original rather than blanking a field.
            if isinstance(v, str) and testo[k] is not None and v.strip() and v != testo[k]:
                aggiornamento[k] = v
        for k in CAMPI_LISTA:
            v = risposta.get(k)
            if (isinstance(v, list) and len(v) == len(testo[k])
                    and all(isinstance(x, str) for x in v) and v != testo[k]):
                aggiornamento[k] = v
        if aggiornamento:
            queue.replace(proposta.id, item.model_copy(update=aggiornamento))
            cambiate += 1
        print(f"[{i}/{len(proposte)}] {proposta.id[:8]} "
              f"{'tradotta' if aggiornamento else 'gia in italiano'}: "
              f"{aggiornamento.get('title', item.title)[:60]}", flush=True)
    print(f"Fatto: {cambiate} proposte tradotte su {len(proposte)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
