#!/bin/bash
# Recreate the lattice-estimator checkouts used by the experiments:
#   estimator-repo/      full clone of https://github.com/malb/lattice-estimator
#   versions/<commit>/   one worktree per estimator version studied in the paper
set -euo pipefail
cd "$(dirname "$0")"
[ -d estimator-repo ] || git clone https://github.com/malb/lattice-estimator.git estimator-repo
# 12 versions of experiment E1: last commit before each half-year boundary 2022-2026,
# the author's laptop copy (a51a410), the deployed copy (3e48ef4) and HEAD at the time (53da598).
for c in 4be104e f9dc7c6 6a96c61 cf36315 c2d5fe9 dfbc622 374f073 5ba00f5 a2be406 a51a410 3e48ef4 53da598; do
  [ -d "versions/$c" ] || git -C estimator-repo worktree add -q --detach "../versions/$c" "$c"
done
# scratch worktree used by bisect_test.sh
[ -d versions/bisect ] || git -C estimator-repo worktree add -q --detach ../versions/bisect 4be104e
echo "ready: $(ls versions | wc -l) checkouts in versions/"
