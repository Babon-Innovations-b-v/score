#!/bin/bash
# Compose and plan one place's still (free, read-only on the store); one JSON line to $STILLS/prep.jsonl.
#   STILLS=<scratch dir> SCORE_REPO=<score checkout> [NEWEST=1] bash prep.sh <place>
# NEWEST=1 composes from the newest made outputs, accepted or not (compose.py --newest).
set -u
P=$1; T=$(cd "$(dirname "$0")" && pwd); PY=${PY:-$SCORE_REPO/.venv/bin/python}
mkdir -p "$STILLS"/{logs,stages,work,out}
if $PY "$T/compose.py" "$P" "$STILLS/stages/$P" ${NEWEST:+--newest} > "$STILLS/logs/compose-$P.log" 2>&1 \
   && $PY "$T/still.py" "$P" "$STILLS/stages/$P/$P" "$STILLS/work/$P" > "$STILLS/logs/plan-$P.log" 2>&1; then
  echo "{\"place\":\"$P\",\"prep\":\"ok\",\"compose\":$(tail -1 "$STILLS/logs/compose-$P.log"),\"plan\":$(tail -1 "$STILLS/logs/plan-$P.log")}" >> "$STILLS/prep.jsonl"
else
  echo "{\"place\":\"$P\",\"prep\":\"failed\"}" >> "$STILLS/prep.jsonl"
fi
