#!/usr/bin/env python3
"""Ricostruisce il registro dei contenuti gia' in coda.

Rattoppo storico, una volta sola: sta in scripts/ e non in learn-core apposta,
perche' non e' un componente della pipeline ma una riparazione del passato.

La data e' la stessa per tutti e viene marcata `seen_at_approximate`: e'
ricostruita, non osservata. Scriverla come se fosse un fatto sarebbe peggio che
non averla, perche' una data finta si legge come vera.
"""
from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime
from pathlib import Path

from suite_learn_core.contents import Content, JsonlContentRegistry
from suite_learn_core.queue import JsonlQueue

_INSTAGRAM = re.compile(r"^instagram:([A-Za-z0-9_-]+)$")


def _url_di(source_id: str) -> str | None:
    """Solo cio' che si puo' derivare davvero. Per il resto: None, non un'ipotesi."""
    match = _INSTAGRAM.match(source_id)
    return f"https://www.instagram.com/reel/{match.group(1)}/" if match else None


def ricostruisci(queue_root: Path, origin: str, quando: datetime) -> int:
    registry = JsonlContentRegistry(queue_root)
    gia_noti = {c.source_id for c in registry.list()}
    sorgenti: dict[str, str] = {}
    for p in JsonlQueue(queue_root).list():
        sorgenti.setdefault(p.item.source_id, p.item.title)

    creati = 0
    for source_id, titolo in sorgenti.items():
        if source_id in gia_noti:
            continue
        registry.append(
            Content(
                source_id=source_id, origin=origin, seen_at=quando,
                seen_at_approximate=True, url=_url_di(source_id), title=titolo,
            )
        )
        creati += 1
    return creati


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-root", type=Path, required=True)
    parser.add_argument("--origin", default="instagram-export")
    args = parser.parse_args()
    quando = datetime.fromtimestamp(
        (args.queue_root / "contentExtractor.jsonl").stat().st_mtime, UTC
    )
    print(f"contenuti ricostruiti: {ricostruisci(args.queue_root, args.origin, quando)}")


if __name__ == "__main__":
    main()
