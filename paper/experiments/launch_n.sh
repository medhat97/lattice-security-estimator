#!/bin/bash
# Launch the n-search replay shards detached (survives the Claude session).
cd "$(dirname "$0")"
SAGE="${SAGE_BIN:-sage}"
for sh in 0 1; do
  setsid nohup "$SAGE" search_study.py n --shard "$sh/2" >> "../data/search/log.n.$sh" 2>&1 < /dev/null &
done
