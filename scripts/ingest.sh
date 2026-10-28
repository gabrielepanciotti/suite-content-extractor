#!/usr/bin/env bash
# Run suite_learn_core from the node root, on the host AND inside the Coordinator
# container. The two can see different paths, so every per-device value is resolved here instead
# of trusting the absolute paths written in .env.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then set -a; . ./.env; set +a; fi

# Level 2: audio skill and Instagram session, falling back to what this box has.
[ -f "${VIDEO_UNDERSTAND_SCRIPT:-}" ] || export VIDEO_UNDERSTAND_SCRIPT="$HOME/.claude/skills/video-understand/scripts/process_video.py"
[ -f "${INSTAGRAM_COOKIES_FILE:-}" ] || export INSTAGRAM_COOKIES_FILE="$ROOT/.secrets/instagram-cookies.txt"
[ -f "$VIDEO_UNDERSTAND_SCRIPT" ] || unset VIDEO_UNDERSTAND_SCRIPT
[ -f "$INSTAGRAM_COOKIES_FILE" ] || unset INSTAGRAM_COOKIES_FILE

# Life sits next to the nodes on a canonical layout; the container mounts it elsewhere.
LIFE=""
for c in "$ROOT/../Life" /workspaces/life; do [ -d "$c/packages/learn-core" ] && { LIFE="$c"; break; }; done
[ -n "$LIFE" ] || { echo "Life non trovato accanto al nodo ne' in /workspaces/life" >&2; exit 2; }

# Inside the Coordinator container there is no whisper (level 2 would read the text
# of the post only). Park the link in a mailbox the host drains with scripts/drain-inbox.sh.
if [ -f /.dockerenv ] && [ "${1:-}" = "ingest" ] && ! command -v whisper >/dev/null 2>&1 && [ -z "${INGEST_FORCE_LOCAL:-}" ]; then
  mkdir -p .learn-queue
  # One line per call, arguments TAB-separated: "$*" joined them with spaces, so the
  # drain re-split `--entita "Life work"` into two words and every link failed.
  (IFS=$'\t'; printf '%s\n' "$*") | flock .learn-queue/da-ingerire.lock tee -a .learn-queue/da-ingerire.txt >/dev/null
  echo "Accodato per l'host (audio e immagini si leggono solo li'): $*" >&2
  echo "In coda di ingestione. Il risultato compare fra un paio di minuti nella coda proposte." 
  exit 0
fi

PY=backend/.venv/bin/python
if ! "$PY" -c 'import suite_learn_core' 2>/dev/null; then
  echo "venv assente o incompleto: lo preparo (una volta sola)" >&2
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -q -r backend/requirements.txt \
    -e "$LIFE/packages/learn-core" -e "$LIFE/packages/backend-core" >&2
fi
# L'obiettivo non e' mai il nodo: senza, il giudice misurava ogni tip sul solo
# ContentExtractor. Una tip vale se serve in qualunque punto dell'ambiente Life.
# L'istanza Life dei record nuovi (ContentExtractor#4): --instance o LIFE_INSTANCE
# vincono; senza, il default del device letto dal registro col lettore di Life.
# Mai un id scritto qui: lo Scheduler ha rietichettato 16 record per un default a mano.
if [ -z "${LIFE_INSTANCE:-}" ]; then
  LIFE_INSTANCE=$("$PY" -c 'import sys; sys.path.append(sys.argv[1]); from suite_core.instances.resolve import resolve; print(resolve().id or "")' "$LIFE/packages/shared" 2>/dev/null) || LIFE_INSTANCE=""
  [ -n "$LIFE_INSTANCE" ] && export LIFE_INSTANCE || unset LIFE_INSTANCE
fi
OBIETTIVO_LIFE="Capire se la tip e' utile nell'intero ambiente di lavoro dell'utente: qualunque nodo, workflow generale, configurazione degli strumenti e qualunque strumento agentico, non solo ContentExtractor."
case "${1:-}" in
  ingest|rejudge)
    case " $* " in *" --obiettivo "*) ;; *) set -- "$@" --obiettivo "$OBIETTIVO_LIFE" ;; esac ;;
esac
exec "$PY" -m suite_learn_core "$@"
