"""Ri-ingerisce i contenuti che la coda ha marcato `failed`, uno alla volta.

Perche' uno script e non un ciclo a mano: l'ingestione di un reel scarica un
video e lo trascrive, quindi dura minuti e puo' fallire a meta'. Un ciclo
lanciato a mano perde il punto in cui si e' fermato e ricomincia dal primo,
ripagando cio' che era gia' riuscito — che e' esattamente il motivo per cui
`rejudge --riprendi` esiste dall'altra parte della pipeline.

Non tocca niente di suo: chiama la stessa CLI che si userebbe a mano, con
l'ambiente giusto (VIDEO_UNDERSTAND_SCRIPT, che vive nel .env del nodo e che
la CLI da sola NON legge — e senza, il livello 2 non parte e il recupero
ripete il fallimento originale senza dirlo).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
CODA = RADICE / ".learn-queue" / "contentExtractor.jsonl"
CONTENUTI = RADICE / ".learn-queue" / "contents.jsonl"

OBIETTIVO = (
    "pratiche E strumenti utili a me: sia il modo di usare Claude Code e gli "
    "altri strumenti di sviluppo (skill, hook, comandi, subagent, prompt, CLI, "
    "MCP), sia strumenti generali (librerie, CLI, servizi) da integrare nei "
    "miei progetti, con i modi concreti di usarli"
)


def _ultima_per_id(percorso: Path) -> dict[str, dict]:
    """L'ultima riga vince: e' la regola della coda append-only."""
    trovate: dict[str, dict] = {}
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(riga)
        except ValueError:
            continue
        trovate[record["id"]] = record
    return trovate


def da_recuperare() -> list[tuple[str, str]]:
    """(source_id, url) dei contenuti che non hanno prodotto nemmeno una tip.

    Un contenuto che ha DUE righe — una fallita e una riuscita — non e' da
    recuperare: il fallimento e' il record di un tentativo, non lo stato del
    contenuto. Recuperarlo comunque rileggerebbe un video gia' letto.
    """
    proposte = _ultima_per_id(CODA).values()
    falliti, riusciti = set(), set()
    for p in proposte:
        (falliti if p["status"] == "failed" else riusciti).add(p["item"]["source_id"])
    url: dict[str, str] = {}
    for riga in CONTENUTI.read_text(encoding="utf-8").splitlines():
        try:
            c = json.loads(riga)
        except ValueError:
            continue
        if c.get("url"):
            url.setdefault(c["source_id"], c["url"])
    return [(s, url[s]) for s in sorted(falliti - riusciti) if s in url]


def main() -> int:
    script = os.environ.get("VIDEO_UNDERSTAND_SCRIPT")
    if not script or not Path(script).exists():
        # Senza livello 2 il recupero e' solo una seconda lettura della
        # didascalia, cioe' esattamente cio' che era gia' fallito. Fermarsi
        # batte sedici ri-fallimenti che sembrano un verdetto.
        print("VIDEO_UNDERSTAND_SCRIPT non impostata o inesistente: "
              "il livello 2 non partirebbe e il recupero ripeterebbe il "
              "fallimento originale.", file=sys.stderr)
        return 1

    lavoro = da_recuperare()
    print(f"Da recuperare: {len(lavoro)} contenuti.", flush=True)
    esiti: list[tuple[str, int]] = []
    for i, (source_id, url) in enumerate(lavoro, 1):
        print(f"\n=== [{i}/{len(lavoro)}] {source_id} — {url}", flush=True)
        done = subprocess.run(
            [sys.executable, "-m", "suite_learn_core", "ingest", url,
             "--node", "contentExtractor", "--origin", "instagram-export",
             "--obiettivo", OBIETTIVO],
            cwd=RADICE, check=False,
        )
        esiti.append((source_id, done.returncode))

    print("\n=== Riepilogo")
    for source_id, codice in esiti:
        print(f"  {'ok ' if codice == 0 else 'ERR'} {source_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
