#!/bin/bash
# git bisect run helper: exit 0 if the commit still gives the OLD (higher) lambda, 1 if NEW.
# usage: bisect_test.sh <spec-json> <threshold>
SAGE="${SAGE_BIN:-sage}"
HERE="$(cd "$(dirname "$0")" && pwd)"
lam=$($SAGE $HERE/run_point.py "$(pwd)" "$1" 2>/dev/null | tail -1 | python3 -c "import json,sys; print(json.load(sys.stdin)['lambda'])" 2>/dev/null)
echo "$(git log -1 --format='%h %ad' --date=short) lambda=$lam" >> $HERE/../data/bisect.log
[ -z "$lam" ] || [ "$lam" = "None" ] && exit 125   # cannot test this commit: skip
python3 -c "import sys; sys.exit(0 if $lam > $2 else 1)"
