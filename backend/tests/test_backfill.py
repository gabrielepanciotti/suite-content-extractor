from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

from suite_learn_core.contents import JsonlContentRegistry
from suite_learn_core.queue import JsonlQueue
from suite_learn_core.types import Item

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from backfill_contents import ricostruisci


def test_it_rebuilds_one_content_per_source(tmp_path):
    queue = JsonlQueue(tmp_path)
    queue.put("contentExtractor", Item(title="a", body="b", source_id="instagram:ABC"))
    queue.put("contentExtractor", Item(title="c", body="d", source_id="instagram:ABC"))
    queue.put("contentExtractor", Item(title="e", body="f", source_id="instagram:XYZ"))

    creati = ricostruisci(tmp_path, "instagram-export", datetime(2026, 9, 1, tzinfo=UTC))

    assert creati == 2
    per_id = {c.source_id: c for c in JsonlContentRegistry(tmp_path).list()}
    assert per_id["instagram:ABC"].url == "https://www.instagram.com/reel/ABC/"
    assert per_id["instagram:ABC"].seen_at_approximate is True


def test_it_does_not_duplicate_what_is_already_registered(tmp_path):
    queue = JsonlQueue(tmp_path)
    queue.put("contentExtractor", Item(title="a", body="b", source_id="instagram:ABC"))
    ricostruisci(tmp_path, "instagram-export", datetime(2026, 9, 1, tzinfo=UTC))
    assert ricostruisci(tmp_path, "instagram-export", datetime(2026, 9, 1, tzinfo=UTC)) == 0


def test_a_non_instagram_source_gets_no_invented_url(tmp_path):
    queue = JsonlQueue(tmp_path)
    queue.put("contentExtractor", Item(title="a", body="b", source_id="text:deadbeef"))
    ricostruisci(tmp_path, "cli", datetime(2026, 9, 1, tzinfo=UTC))
    (only,) = JsonlContentRegistry(tmp_path).list()
    assert only.url is None
