"""Un device finto con due istanze, per ogni test: mai il registro vero di chi li lancia."""
from __future__ import annotations

import json

import pytest


@pytest.fixture(autouse=True)
def device_con_due_istanze(tmp_path_factory, monkeypatch):
    home = tmp_path_factory.mktemp("life-home")
    alfa = tmp_path_factory.mktemp("life-alfa")
    (alfa / "instance.config.json").write_text(
        json.dumps({"channels": {"telegram": {"chatId": "-100123"}, "bus": {"tenant": "alfa"}}}),
        encoding="utf-8",
    )
    (home / "instances.json").write_text(json.dumps({
        "version": 1,
        "instances": {
            "alfa": {"path": str(alfa), "profile": "work", "band": 1},
            "beta": {"path": str(home / "manca"), "profile": "personal", "band": 2},
        },
    }), encoding="utf-8")
    (home / "state.json").write_text(
        json.dumps({"version": 1, "default": "alfa", "nextBand": 3}), encoding="utf-8"
    )
    monkeypatch.setenv("LIFE_HOME", str(home))
    monkeypatch.delenv("LIFE_INSTANCE", raising=False)
    return home
