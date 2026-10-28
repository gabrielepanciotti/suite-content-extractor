#!/usr/bin/env bash
# Host side of the ingest mailbox: runs every parked link with the full level 2.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PATH="$HOME/.local/bin:$PATH"
BOX=.learn-queue/da-ingerire.txt
exec 9>.learn-queue/da-ingerire.lock
flock -n 9 || exit 0            # a previous drain is still reading videos

# Boxes of other devices (ContentExtractor#1): the personal Coordinator runs on the
# minipc, which cannot open a connection to this box, while this box reaches it over
# ssh. So the link stays parked over there and the drain fetches it, stamped with the
# instance it came from: one queue, one running copy, no second instance.
# INGEST_REMOTE_BOXES="<instance>,<ssh host>,<box path on the host>[,<entita>];..."
# The box moves to .transito under the writer's lock and is removed only after it is
# appended here: a dropped connection re-reads it, it never loses it.
[ -n "${INGEST_REMOTE_BOXES:-}" ] || INGEST_REMOTE_BOXES=$(sed -n 's/^INGEST_REMOTE_BOXES=//p' .env 2>/dev/null | tr -d '"')
IFS=';' read -r -a remote_boxes <<< "${INGEST_REMOTE_BOXES:-}"
for spec in "${remote_boxes[@]}"; do
  IFS=',' read -r inst host rbox entita <<< "$spec"
  [ -n "$inst" ] && [ -n "$host" ] && [ -n "$rbox" ] || continue
  rdir=$(dirname "$rbox"); rname=$(basename "$rbox")
  extra=$'\t--instance\t'"$inst"
  [ -n "${entita:-}" ] && extra+=$'\t--entita\t'"$entita"
  if lines=$(ssh -o BatchMode=yes -o ConnectTimeout=8 "$host" \
      "cd '$rdir' 2>/dev/null || exit 0; flock da-ingerire.lock sh -c '[ -s $rname ] && cat $rname >> $rname.transito; : > $rname' 2>/dev/null; [ -f $rname.transito ] && cat $rname.transito; exit 0"); then
    if [ -n "$lines" ]; then
      while IFS= read -r l; do [ -n "$l" ] && printf '%s%s\n' "$l" "$extra"; done <<< "$lines" >> "$BOX"
      ssh -o BatchMode=yes -o ConnectTimeout=8 "$host" "rm -f '$rdir/$rname.transito'" \
        || echo "casella $host: letta ma non svuotata, la prossima volta la rilegge" >> .learn-queue/drain.log
      echo "casella $host ($inst): $(wc -l <<< "$lines") link" >> .learn-queue/drain.log
    fi
  else
    echo "casella $host ($inst): non raggiungibile" >> .learn-queue/drain.log
  fi
done
[ -s "$BOX" ] || exit 0
while true; do
  line=$(head -n1 "$BOX") || break
  [ -n "$line" ] || break
  # Arguments are TAB-separated (see ingest.sh). A line without a TAB was parked by
  # the old format: split it on spaces as before.
  if [[ "$line" == *$'\t'* ]]; then IFS=$'\t' read -r -a args <<< "$line"
  else read -r -a args <<< "$line"; fi
  scripts/ingest.sh "${args[@]}" >> .learn-queue/drain.log 2>&1 || echo "FALLITO: ${args[*]}" >> .learn-queue/drain.log
  tail -n +2 "$BOX" > "$BOX.tmp" && mv "$BOX.tmp" "$BOX"
done
