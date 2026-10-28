"""Le istanze Life che questo operatore serve (ContentExtractor#4).

Contratto: spec di Life `2026-10-14-framework-operatore-istanza-design.md` §4.
Una sola copia del nodo serve ogni istanza registrata sul device: le istanze
si leggono dal registro (`~/.life/instances.json`, o `$LIFE_HOME`) e i loro
canali dalla `instance.config.json` di ciascuna — sempre con il lettore unico di
Life, `suite_core.instances`, mai con un parsing proprio.

`suite_core` non si installa nel venv dei nodi: si importa dal checkout di Life
da cui viene `learn-core` (stessa radice, quindi stessa versione), o da
`LIFE_FRAMEWORK_ROOT` quando la si vuole indicare. E' lo schema del
Coordinator (`bus_agents._import_local_agents`).
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import suite_learn_core

logger = logging.getLogger(__name__)


class RegistroNonDisponibile(Exception):
    """`suite_core` non si importa o il registro non si legge: un guasto, non un'istanza in meno."""


class IstanzaSconosciuta(Exception):
    """Un id che sul device non e' registrato (R-1). Porta gli id validi."""

    def __init__(self, istanza: str, validi: list[str]) -> None:
        self.istanza = istanza
        self.validi = validi
        super().__init__(
            f"istanza {istanza!r} non registrata su questo device. "
            f"Validi: {', '.join(validi) or '(nessuno)'}"
        )


def life_root() -> Path:
    """Il checkout di Life: `LIFE_FRAMEWORK_ROOT`, altrimenti quello di learn-core."""
    env = os.environ.get("LIFE_FRAMEWORK_ROOT")
    if env:
        return Path(env)
    # .../Life/packages/learn-core/suite_learn_core/__init__.py
    return Path(suite_learn_core.__file__).resolve().parents[3]


def _suite() -> ModuleType:
    shared = life_root() / "packages" / "shared"
    if str(shared) not in sys.path:
        sys.path.append(str(shared))
    try:
        import suite_core.instances as instances
        import suite_core.instances.store  # noqa: F401 - load_registry/load_state
    except Exception as exc:  # un import rotto dentro Life resta «non disponibile»
        raise RegistroNonDisponibile(
            f"suite_core.instances non importabile da {shared}: {exc}"
        ) from exc
    return instances


def registrate() -> dict:
    """Le istanze del registro, per id. Vuoto se il device non ne ha."""
    suite = _suite()
    try:
        trovate, avvisi = suite.store.load_registry()
    except suite.model.InstanceError as exc:
        raise RegistroNonDisponibile(str(exc)) from exc
    for avviso in avvisi:
        logger.warning("registro istanze: %s", avviso)
    return trovate


def default_id() -> str | None:
    """Il default del device (`state.json`), se nomina un'istanza registrata."""
    suite = _suite()
    try:
        scelto = suite.store.load_state().get("default")
    except suite.model.InstanceError as exc:
        raise RegistroNonDisponibile(str(exc)) from exc
    return scelto if isinstance(scelto, str) and scelto in registrate() else None


def validi() -> list[str]:
    return sorted(registrate())


def per_lettura(istanza: str | None) -> str | None:
    """Il filtro `?instance=`: assente vuol dire tutte, sconosciuto e' un errore."""
    if not istanza:
        return None
    if istanza not in registrate():
        raise IstanzaSconosciuta(istanza, validi())
    return istanza


def per_scrittura(istanza: str | None) -> str:
    """L'istanza di una scrittura: quella dichiarata, o il default del device.

    Il default vale con un avviso nel log: una scrittura che non dice a chi
    appartiene e' una deriva da vedere, non un errore che blocca chi chiama
    da prima del contratto. Senza default, invece, non si indovina.
    """
    if istanza:
        if istanza not in registrate():
            raise IstanzaSconosciuta(istanza, validi())
        return istanza
    scelto = default_id()
    if scelto is None:
        raise IstanzaSconosciuta("", validi())
    logger.warning("scrittura senza istanza: la attribuisco al default del device %r", scelto)
    return scelto


def di(record_instance_id: str | None) -> str | None:
    """L'istanza di un record. Le righe senza (anteriori al contratto) sono del default.

    Rete di sicurezza: dopo `scripts/utility/assegna_istanza.py` non ce ne sono.
    """
    return record_instance_id or default_id()


@dataclass(frozen=True)
class Vista:
    """Un'istanza come la vede l'API: anche quando non risponde, con il motivo."""

    id: str
    status: str
    reason: str | None
    default: bool
    profile: str
    channels: dict
    channel_problems: list[str]


def elenco() -> list[Vista]:
    """Tutte le istanze registrate. Una irraggiungibile c'e', con il motivo (degrado nominato)."""
    suite = _suite()
    predefinita = default_id()
    out: list[Vista] = []
    for iid, inst in sorted(registrate().items()):
        path = Path(inst.path)
        if not path.is_dir():
            status, reason = "unreachable", f"path assente: {path.as_posix()}"
            canali, problemi = {}, []
        else:
            status, reason = "ok", None
            letti = suite.channels_at(iid, path)
            canali = {k: v for k, v in letti.to_dict().items() if k not in ("instance_id", "problems")}
            problemi = list(letti.problems)
        out.append(Vista(iid, status, reason, iid == predefinita, inst.profile, canali, problemi))
    return out
