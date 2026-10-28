"""Il materiale che arriva dopo: il file promesso, il link dietro l'azione.

Metà dei post buoni non si legge da soli. «Commenta AGENTIC e ti mando il
cheatsheet» consegna solo a chi commenta, e commentare richiede una persona
loggata: nessun motore può farlo. Finora quel materiale non aveva un posto
dove entrare — l'unica strada era ingerirlo come contenuto NUOVO, che nasceva
scollegato dal post e dal giudizio già dato.

Qui il materiale entra **sul contenuto che lo aspettava** (`--allega-a`), e
l'attesa è gestita come si gestisce un lavoro lungo: la richiesta HTTP non
aspetta l'estrazione. Un'ingestione dura minuti — scarica, legge, giudica,
espande — e una richiesta che resta appesa a tutto questo scade nel browser
molto prima, lasciando il lavoro a metà e nessuno a raccoglierne l'esito.
Quindi: il processo parte staccato, lo stato vive in un file, e la pagina lo
chiede finché non è finito.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

Stato = Literal["in_corso", "finita", "fallita"]

OBIETTIVO = (
    "pratiche E strumenti utili a me: sia il modo di usare Claude Code e gli "
    "altri strumenti di sviluppo (skill, hook, comandi, subagent, prompt, CLI, "
    "MCP), sia strumenti generali (librerie, CLI, servizi) da integrare nei "
    "miei progetti, con i modi concreti di usarli"
)
"""L'obiettivo con cui si giudica ciò che arriva da qui.

Lo stesso del recupero e dell'ultimo rigiudizio: se il materiale nuovo venisse
giudicato con un obiettivo diverso da quello delle tip già sulla scheda, la
stessa scheda porterebbe due verdetti incomparabili.
"""

ESTENSIONI = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md", ".html"}
"""Ciò che l'estrattore sa leggere. Un .zip o un .docx entrerebbe e basta."""

MAX_BYTE = 25 * 1024 * 1024


class MaterialeRifiutato(ValueError):
    """Il materiale non è utilizzabile, e il motivo si legge."""


@runtime_checkable
class Lanciatore(Protocol):
    def avvia(self, argv: list[str], cwd: Path, log: Path) -> int: ...


class LanciatoreStaccato:
    """Avvia davvero, e non aspetta. È il bordo: nessun test lo esercita."""

    def avvia(self, argv: list[str], cwd: Path, log: Path) -> int:
        log.parent.mkdir(parents=True, exist_ok=True)
        handle = log.open("w")
        processo = subprocess.Popen(  # noqa: S603 — argv è costruito qui, non ricevuto
            argv, cwd=str(cwd), stdout=handle, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        return processo.pid


class LanciatoreFinto:
    """Registra cosa sarebbe partito. Per i test, che non devono spendere."""

    def __init__(self) -> None:
        self.avvii: list[list[str]] = []

    def avvia(self, argv: list[str], cwd: Path, log: Path) -> int:
        self.avvii.append(list(argv))
        return 0


@dataclass
class Lavoro:
    source_id: str
    stato: Stato
    materiale: str
    quando: str
    esito: str | None = None
    pid: int | None = None

    def json(self) -> dict:
        return {
            "source_id": self.source_id, "stato": self.stato,
            "materiale": self.materiale, "quando": self.quando,
            "esito": self.esito, "pid": self.pid,
        }


def _slug(source_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in source_id)


def cartella_allegati(root: Path) -> Path:
    return root / "allegati"


def _file_stato(root: Path, source_id: str) -> Path:
    return cartella_allegati(root) / _slug(source_id) / "lavoro.json"


def salva_file(root: Path, source_id: str, nome: str, dati: bytes) -> Path:
    """Scrive l'allegato accanto agli altri di quel contenuto.

    Il nome arriva da un browser, quindi non è un nome: è testo che può
    contenere `..` o una barra e uscire dalla cartella. Si tiene solo l'ultimo
    segmento, e l'estensione decide se il file è leggibile — un .zip entrerebbe
    e resterebbe lì senza che nessuno possa farci niente.
    """
    pulito = Path(nome).name.replace("\\", "_").strip() or "allegato"
    estensione = Path(pulito).suffix.lower()
    if estensione not in ESTENSIONI:
        raise MaterialeRifiutato(
            f"«{estensione or 'senza estensione'}» non è un formato che so leggere: "
            + ", ".join(sorted(ESTENSIONI))
        )
    if len(dati) > MAX_BYTE:
        raise MaterialeRifiutato(
            f"il file supera i {MAX_BYTE // (1024 * 1024)} MB"
        )
    if not dati:
        raise MaterialeRifiutato("il file è vuoto")

    cartella = cartella_allegati(root) / _slug(source_id)
    cartella.mkdir(parents=True, exist_ok=True)
    destinazione = cartella / pulito
    destinazione.write_bytes(dati)
    return destinazione


def leggi_lavoro(root: Path, source_id: str) -> Lavoro | None:
    """Lo stato dell'ultima ri-estrazione su questo contenuto, se c'è stata."""
    percorso = _file_stato(root, source_id)
    if not percorso.is_file():
        return None
    try:
        dati = json.loads(percorso.read_text())
    except (OSError, json.JSONDecodeError):
        # Uno stato illeggibile non è una ri-estrazione fallita: è uno stato
        # che non sappiamo. Dirlo «fallita» accuserebbe un lavoro che magari
        # è andato benissimo.
        return None
    return Lavoro(**dati)


def scrivi_lavoro(root: Path, lavoro: Lavoro) -> None:
    percorso = _file_stato(root, lavoro.source_id)
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text(json.dumps(lavoro.json(), ensure_ascii=False, indent=1))


def avvia(
    root: Path,
    source_id: str,
    materiale: str,
    *,
    node_id: str,
    lanciatore: Lanciatore,
    radice_nodo: Path,
    istanza: str | None = None,
) -> Lavoro:
    """Fai ripartire l'estrazione su *materiale*, agganciata a *source_id*.

    `sys.executable`, non «python»: il comando gira dentro il venv del backend,
    dove `suite_learn_core` è installato. Un «python» nudo prenderebbe quello
    di sistema e morirebbe su un ImportError — è già successo, scritto nelle
    istruzioni del bot Telegram.
    """
    argv = [
        sys.executable, "-m", "suite_learn_core", "ingest", materiale,
        "--node", node_id,
        "--origin", "cli",
        "--allega-a", source_id,
        "--obiettivo", os.environ.get("LEARN_OBIETTIVO") or OBIETTIVO,
    ]
    if istanza:
        # Le tip nuove restano nell'istanza del contenuto a cui si agganciano.
        argv += ["--instance", istanza]
    log = cartella_allegati(root) / _slug(source_id) / "ingest.log"
    pid = lanciatore.avvia(argv, radice_nodo, log)
    lavoro = Lavoro(
        source_id=source_id, stato="in_corso", materiale=materiale,
        quando=datetime.now(UTC).isoformat(), pid=pid or None,
    )
    scrivi_lavoro(root, lavoro)
    return lavoro


def aggiorna_da_log(root: Path, lavoro: Lavoro, tip_dopo: int) -> Lavoro:
    """Lo stato vero, letto dal log del processo invece che promesso.

    Nessuno avvisa quando il sottoprocesso finisce: il file di stato direbbe
    «in_corso» per sempre. La riga finale del CLI («N proposte in coda…») è
    la prova che è arrivato in fondo; *tip_dopo* dice se quel passaggio ha
    davvero lasciato qualcosa sulla scheda.
    """
    if lavoro.stato != "in_corso":
        return lavoro
    log = cartella_allegati(root) / _slug(lavoro.source_id) / "ingest.log"
    if not log.is_file():
        return lavoro
    testo = log.read_text(errors="replace")
    if "proposte in coda" in testo:
        lavoro.stato = "finita"
        lavoro.esito = f"{tip_dopo} tip sulla scheda dopo la ri-estrazione"
    elif "Traceback" in testo or "Nessun motore LLM" in testo:
        # L'ultima riga non vuota: è quella che dice cosa è andato storto,
        # e ficcare l'intero traceback in una scheda non aiuta nessuno.
        righe = [r for r in testo.splitlines() if r.strip()]
        lavoro.stato = "fallita"
        lavoro.esito = righe[-1][:200] if righe else "il processo è morto"
    elif lavoro.pid and not vivo(lavoro.pid):
        # Il processo non c'e' piu' e non ha scritto la riga finale: l'ha
        # fermato qualcuno da fuori (un riavvio del servizio). Senza questo
        # la pagina direbbe «in corso» per sempre su un lavoro morto.
        lavoro.stato = "fallita"
        lavoro.esito = "interrotta: il processo si e' fermato prima di finire, riprova ad aggiungere la fonte"
    else:
        return lavoro
    scrivi_lavoro(root, lavoro)
    return lavoro


def vivo(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
