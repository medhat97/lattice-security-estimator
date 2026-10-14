"""
Run the three lattice-estimator attacks used by the web tool on one LWE
parameter set, with one specific lattice-estimator checkout.

Usage (inside Sage):  sage run_point.py <estimator_path> '<spec json>'
Prints one JSON line. Written to work across lattice-estimator versions
from 2021 to 2026, so it only uses API that exists in all of them.
"""
import json
import math
import sys
import time

est_path, spec = sys.argv[1], json.loads(sys.argv[2])
sys.path.insert(0, est_path)

from estimator import LWE  # noqa: E402

try:
    from estimator import ND
except ImportError:  # very old versions only export the full name
    from estimator.nd import NoiseDistribution as ND


def dist(d):
    kind, val = d["type"], d.get("param")
    if kind == "cbd":
        return ND.CenteredBinomial(int(val))
    if kind == "gauss":
        return ND.DiscreteGaussian(float(val))
    if kind == "ternary":
        return ND.Uniform(-1, 1)
    if kind == "binary":
        return ND.Uniform(0, 1)
    raise ValueError(kind)


kw = dict(n=int(spec["n"]), q=int(spec["q"]), Xs=dist(spec["xs"]), Xe=dist(spec["xe"]))
if spec.get("m") is not None:
    kw["m"] = int(spec["m"])
params = LWE.Parameters(**kw)

out = {"label": spec.get("label"), "attacks": {}}
for name in spec.get("attacks", ["primal_usvp", "primal_bdd", "dual_hybrid"]):
    t0 = time.time()
    try:
        r = getattr(LWE, name)(params)
        rop = float(r["rop"])
        rec = {"rop_log2": math.log2(rop) if rop > 0 else None}
        for key in ("beta", "d", "m", "zeta", "eta"):
            try:
                rec[key] = int(r[key])
            except (KeyError, TypeError, ValueError):
                pass
    except Exception as e:  # one attack failing must not abort the others
        rec = {"error": f"{type(e).__name__}: {e}"[:300]}
    rec["seconds"] = round(time.time() - t0, 2)
    out["attacks"][name] = rec

vals = [a["rop_log2"] for a in out["attacks"].values() if a.get("rop_log2") is not None]
out["lambda"] = min(vals) if vals else None
print(json.dumps(out))
