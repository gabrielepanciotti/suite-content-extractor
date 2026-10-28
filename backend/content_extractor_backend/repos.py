"""From the name a judgement gives ("Life", "~/.claude") to a GitHub repo.

The judge names where a practice belongs the way a person would — a folder
name, `~/.claude`, sometimes a whole sentence — while `gh` needs `owner/repo`.
Passing the judge's words straight through is how an approval turned into
"could not resolve a repository named 'Life (packages/learn-core'".

The map is read from the checkouts on this device, not written down: the
nodes next to this one and `~/.claude`, each with its own `origin`. A repo
that exists on GitHub but not here cannot be offered, and that is fine — it
is not a repo anyone here would open an issue in without cloning it first.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from suite_learn_core.review import GhRepoChecker, RepoChecker

NODE_ROOT = Path(__file__).resolve().parents[2]
CLAUDE_KEY = "~/.claude"
_GITHUB = re.compile(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?/?$")
_SLUG = re.compile(r"^[\w.-]+/[\w.-]+$")


class Repo(BaseModel):
    nome: str
    """How a person calls it: the folder name, or `~/.claude`."""
    slug: str
    """`owner/repo`, what `gh --repo` wants."""
    ambito: str | None = None
    """`work`, `personal`, `entrambi` (checkout in both) or `globale` (~/.claude)."""
    esiste: bool = True
    """False when GitHub does not know the repo: a local `origin` that points
    nowhere. An issue cannot be opened there, so the page offers it disabled."""
    motivo: str | None = None
    """Why `esiste` is false, in Italian."""


def _piega(nome: str) -> str:
    return "".join(c for c in nome.casefold() if c.isalnum())


def _origin(cartella: Path) -> str | None:
    try:
        url = subprocess.run(
            ["git", "-C", str(cartella), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    trovato = _GITHUB.search(url)
    return trovato.group(1) if trovato else None


@lru_cache(maxsize=1)
def conosciuti() -> tuple[Repo, ...]:
    """Every repo an issue can be opened in from here, by the name people use."""
    env = os.environ.get("LEARN_REPOS_DIR")
    if env:
        cartelle = [Path(p) for p in env.split(os.pathsep) if p]
    else:
        # Personal checkouts sit next to this node; the work ones in `work`
        # next to `personal`. An issue is opened where the code is, and the
        # code of this person lives in both.
        # Whichever of the two this node itself sits in, both are searched.
        casa = NODE_ROOT.parent.parent
        cartelle = [casa / "personal", casa / "work"]
    trovati: dict[str, Repo] = {}
    claude = Path.home() / ".claude"
    if (slug := _origin(claude)) is not None:
        trovati[CLAUDE_KEY] = Repo(nome=CLAUDE_KEY, slug=slug, ambito="globale")
    for radice in (c for c in cartelle if c.is_dir()):
        ambito = radice.name if radice.name in ("work", "personal") else None
        for cartella in sorted(p for p in radice.iterdir() if (p / ".git").exists()):
            slug = _origin(cartella)
            if slug is None:
                continue
            noto = next((k for k, r in trovati.items() if r.slug == slug), None)
            if noto is not None:
                # Same repo seen from the other side: it is in both.
                if trovati[noto].ambito in ("work", "personal") and trovati[noto].ambito != ambito:
                    trovati[noto] = trovati[noto].model_copy(update={"ambito": "entrambi"})
                continue
            trovati.setdefault(cartella.name, Repo(nome=cartella.name, slug=slug, ambito=ambito))
    return tuple(trovati.values())


def risolvi(testo: str | None) -> Repo | None:
    """The repo *testo* names, or None when it names none of the known ones.

    Tolerant of how judges actually write: `owner/repo`, a folder name in any
    case, `~/.claude`, or a name followed by an explanation in brackets
    ("Life (packages/learn-core, …)"). Anything else is None — guessing a repo
    opens an issue somewhere nobody asked.
    """
    if not testo:
        return None
    testo = testo.strip()
    repos = conosciuti()
    if testo.startswith(CLAUDE_KEY):
        return next((r for r in repos if r.nome == CLAUDE_KEY), None)
    if testo.startswith(("/", "~/")) or re.match(r"^[A-Za-z]:[\\/]", testo):
        # A checkout path ("/path/to/ContentExtractor"): the repo is
        # its last folder. Judges wrote these for eleven proposals, and each
        # one read "no repo" although it named a checkout that is right here.
        testo = re.split(r"[\\/]", testo.rstrip("/\\"))[-1]
    if _SLUG.match(testo):
        return next((r for r in repos if r.slug.casefold() == testo.casefold()),
                    Repo(nome=testo.split("/")[1], slug=testo))
    testa = re.split(r"[\s(,;:]", testo, maxsplit=1)[0]
    chiave = _piega(testa)
    return next((r for r in repos if _piega(r.nome) == chiave), None)


class RepoCheckerCache:
    """`GhRepoChecker` with an expiry, for a long-lived server.

    The plain checker caches forever, which is right for one command and wrong
    for a process that lives for weeks: a repo created an hour ago would stay
    "missing" until a restart. A yes is kept long (it rarely turns into a no),
    a no is kept briefly (the person is probably about to create it).
    """

    def __init__(self, ok_ttl: float = 600.0, ko_ttl: float = 30.0, factory=GhRepoChecker) -> None:
        self._ok_ttl, self._ko_ttl, self._factory = ok_ttl, ko_ttl, factory
        self._seen: dict[str, tuple[bool, float]] = {}

    def exists(self, repo: str) -> bool:
        found = self._seen.get(repo)
        now = time.monotonic()
        if found is not None and now - found[1] < (self._ok_ttl if found[0] else self._ko_ttl):
            return found[0]
        risposta = self._factory().exists(repo)
        self._seen[repo] = (risposta, now)
        return risposta


def con_esistenza(repos: list[Repo], checker: RepoChecker) -> list[Repo]:
    """Each repo marked with whether GitHub knows it, checked in parallel."""
    if not repos:
        return []
    with ThreadPoolExecutor(max_workers=8) as pool:
        esistono = list(pool.map(lambda r: checker.exists(r.slug), repos))
    return [
        r if ok else r.model_copy(update={
            "esiste": False, "motivo": f"il repo {r.slug} non esiste su GitHub",
        })
        for r, ok in zip(repos, esistono)
    ]
