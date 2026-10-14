"""
Evaluate many parameter sets in one Sage process (avoids ~5 s Sage start-up
per point). Same attacks and lambda definition as run_point.py / the tool.

Usage (inside Sage):  sage run_batch.py <estimator_path> <specs.jsonl> <out.jsonl>
Each input line is a spec with a unique "key". Keys already present in
out.jsonl are skipped, so an interrupted run can simply be restarted.
"""
import json
import math
import os
import sys
import time

est_path, spec_file, out_file = sys.argv[1:4]
sys.path.insert(0, est_path)

from estimator import LWE, ND  # noqa: E402


def dist(d):
    kind, val = d["type"], d.get("param")
    if kind == "cbd":
        return ND.CenteredBinomial(int(val))
    if kind == "gauss":
        return ND.DiscreteGaussian(float(val))
    if kind == "ternary":
        return ND.Uniform(-1, 1)
    raise ValueError(kind)


done = set()
if os.path.exists(out_file):
    with open(out_file) as fh:
        done = {json.loads(line)["key"] for line in fh if line.strip()}

with open(spec_file) as fh:
    specs = [json.loads(line) for line in fh if line.strip()]

with open(out_file, "a") as out:
    for spec in specs:
        if spec["key"] in done:
            continue
        kw = dict(n=int(spec["n"]), q=int(spec["q"]), Xs=dist(spec["xs"]), Xe=dist(spec["xe"]))
        if spec.get("m") is not None:
            kw["m"] = int(spec["m"])
        params = LWE.Parameters(**kw)
        rec = {"key": spec["key"], "attacks": {}}
        for name in ("primal_usvp", "primal_bdd", "dual_hybrid"):
            t0 = time.time()
            try:
                r = getattr(LWE, name)(params)
                rop = float(r["rop"])
                a = {"rop_log2": math.log2(rop) if rop > 0 else None}
                for k in ("beta", "d", "zeta"):
                    try:
                        a[k] = int(r[k])
                    except (KeyError, TypeError, ValueError):
                        pass
            except Exception as e:
                a = {"error": f"{type(e).__name__}: {e}"[:200]}
            a["seconds"] = round(time.time() - t0, 3)
            rec["attacks"][name] = a
        vals = [a["rop_log2"] for a in rec["attacks"].values() if a.get("rop_log2") is not None]
        rec["lambda"] = min(vals) if vals else None
        out.write(json.dumps(rec) + "\n")
        out.flush()
