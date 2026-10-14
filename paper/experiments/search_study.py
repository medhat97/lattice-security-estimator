"""
Experiment 2 (search): replay the web tool's "Find parameter" algorithms
(copied from backend/sage_worker/find_worker.py, same bounds) and a
safeguarded secant search on the same lambda oracle, for many targets.

Runs inside Sage:
  sage search_study.py <param: n|sigma|q|k> [--shard i/N]

The lambda oracle is seeded from ../data/grids/<param>.jsonl; points not on
the grid are evaluated live with the deployed estimator version (3e48ef4)
and appended to ../data/grids/<param>.live.jsonl, so reruns reuse them.
Results: ../data/search/<param>[.shard].jsonl, one line per (target, algorithm).
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "versions" / "3e48ef4"))
from estimator import LWE, ND  # noqa: E402

GRIDS = HERE.parent / "data" / "grids"
OUT = HERE.parent / "data" / "search"

# fixed parameters of each experiment (must match grid_study.py)
FIXED = {
    "n":     dict(q=3329, xs=("cbd", 2), xe=("cbd", 2)),
    "sigma": dict(n=640, q=2**15),
    "q":     dict(n=640, xs=("gauss", 2.8), xe=("gauss", 2.8)),
    "k":     dict(base=256, q=3329, xs=("cbd", 2), xe=("cbd", 2)),
}


def dist(kind, val):
    return ND.CenteredBinomial(int(val)) if kind == "cbd" else ND.DiscreteGaussian(float(val))


def lwe_for(param, x):
    if param == "n":
        f = FIXED["n"]
        return LWE.Parameters(n=int(x), q=f["q"], Xs=dist(*f["xs"]), Xe=dist(*f["xe"]))
    if param == "sigma":
        f = FIXED["sigma"]
        d = ND.DiscreteGaussian(float(x))
        return LWE.Parameters(n=f["n"], q=f["q"], Xs=d, Xe=d)
    if param == "q":
        f = FIXED["q"]
        return LWE.Parameters(n=f["n"], q=int(x), Xs=dist(*f["xs"]), Xe=dist(*f["xe"]))
    if param == "k":
        f = FIXED["k"]
        return LWE.Parameters(n=f["base"] * int(x), q=f["q"], Xs=dist(*f["xs"]), Xe=dist(*f["xe"]))
    raise ValueError(param)


def key_of(param, x):
    return f"sigma={x:.1f}" if param == "sigma" else f"{param}={int(x)}"


class Oracle:
    """lambda(x) with a persistent cache; counts every call an algorithm makes."""

    def __init__(self, param, live_file):
        self.param, self.live_file = param, live_file
        self.cache = {}
        for f in (GRIDS / f"{param}.jsonl", live_file):
            if f.exists():
                for line in f.read_text().splitlines():
                    r = json.loads(line)
                    self.cache[r["key"]] = r["lambda"]
        self.calls = 0
        self.seen = set()

    def reset(self):
        self.calls, self.seen = 0, set()

    def __call__(self, x):
        self.calls += 1
        k = key_of(self.param, x)
        self.seen.add(k)
        if k not in self.cache:
            best = None
            try:
                p = lwe_for(self.param, x)
                for atk in (LWE.primal_usvp, LWE.dual_hybrid, LWE.primal_bdd):
                    try:
                        rop = float(atk(p)["rop"])
                        v = math.log2(rop) if rop > 0 else None
                        if v is not None and (best is None or v < best):
                            best = v
                    except Exception:
                        pass
            except Exception:
                best = None
            self.cache[k] = best
            with open(self.live_file, "a") as fh:
                fh.write(json.dumps({"key": k, "lambda": best}) + "\n")
        return self.cache[k]


# ── the tool's algorithms, verbatim logic from find_worker.py (LWE, no ring rounding) ──

def tool_find_n(lam, target):
    lo, hi = 64, 4096
    if lam(hi) is None or lam(hi) < target:
        return None
    result = hi
    while lo <= hi:
        mid = (lo + hi) // 2
        val = lam(mid)
        if val is not None and val >= target:
            result, hi = mid, mid - 1
        else:
            lo = mid + 1
    lam(result)                      # tool re-evaluates for its verification output
    if result > 64:
        lam(result - 1)
    return result


def tool_find_sigma(lam, target):
    lo_s, hi_s = 0.5, 30.0
    f = lambda s: lam(round(s, 1))   # noqa: E731  (tool rounds sigma to 0.1)
    if f(hi_s) is None or f(hi_s) < target:
        return None
    result = hi_s
    while hi_s - lo_s > 0.1:
        mid = (lo_s + hi_s) / 2
        val = f(mid)
        if val is not None and val >= target:
            result, hi_s = mid, mid
        else:
            lo_s = mid
    result = round(result, 1)
    f(result)
    if result > 0.5:
        f(round(result - 0.1, 1))
    return result


def tool_find_q(lam, target):
    lo, hi = 1024, 2**18
    if lam(hi) is not None and lam(hi) >= target:
        return hi
    lam_lo = lam(lo)
    if lam_lo is None or lam_lo < target:
        return None
    result = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        val = lam(mid)
        if val is not None and val >= target:
            result, lo = mid, mid + 1
        else:
            hi = mid - 1
    lam(result)
    if result + 256 <= 2**18:
        lam(result + 256)
    return result


def tool_find_k(lam, target):
    for k in range(1, 17):
        val = lam(k)
        if val is not None and val >= target:
            if k > 1:
                lam(k - 1)
            return k
    return None


# ── safeguarded secant (regula falsi, Illinois) on an ordered domain ─────────

def secant_search(lam, domain, target, transform):
    """Smallest index i with lam(domain[i]) >= target, assuming lam increases
    along the domain. Interpolates in transform(x); falls back to bisection
    when a step fails to halve the bracket. Both bracket ends are evaluated,
    so lam(answer) and lam(step before answer) come for free."""
    lo, hi = 0, len(domain) - 1
    g = lambda i: (lambda v: -math.inf if v is None else v - target)(lam(domain[i]))  # noqa: E731
    g_lo, g_hi = g(lo), g(hi)
    if g_hi < 0:
        return None
    if g_lo >= 0:
        return domain[lo]
    side, slow = 0, 0
    while hi - lo > 1:
        width = hi - lo
        if math.isinf(g_lo) or slow >= 2:
            i = (lo + hi) // 2
            slow = 0
        else:
            t_lo, t_hi = transform(domain[lo]), transform(domain[hi])
            t_star = t_hi - g_hi * (t_hi - t_lo) / (g_hi - g_lo)
            # map t_star back to the nearest index by bisection on the (monotone) transform
            a, b = lo, hi
            while b - a > 1:
                c = (a + b) // 2
                if (transform(domain[c]) - t_star) * (t_hi - t_lo) <= 0:
                    a = c
                else:
                    b = c
            i = a if abs(transform(domain[a]) - t_star) <= abs(transform(domain[b]) - t_star) else b
            i = min(max(i, lo + 1), hi - 1)
        gi = g(i)
        if gi >= 0:
            hi, g_hi = i, gi
            if side == 1:
                g_lo /= 2            # Illinois: shrink the stale endpoint
            side = 1
        else:
            lo, g_lo = i, gi
            if side == -1:
                g_hi /= 2
            side = -1
        slow = slow + 1 if (hi - lo) > width / 2 else 0
    return domain[hi]


def itp_search(lam, domain, target, transform, to_index, n0=1):
    """ITP root finding (Oliveira & Takahashi, ACM TOMS 2021) on an ordered
    integer-indexed domain: interpolate (regula falsi in transform(x)),
    truncate, then project onto a shrinking ball around the midpoint. The
    projection keeps the number of steps within n0 of bisection's, so the
    flat regions that stall plain regula falsi cannot blow up the cost."""
    lo, hi = 0, len(domain) - 1
    g = lambda i: (lambda v: -math.inf if v is None else v - target)(lam(domain[i]))  # noqa: E731
    g_lo, g_hi = g(lo), g(hi)
    if g_hi < 0:
        return None
    if g_lo >= 0:
        return domain[lo]
    eps = 0.5                                   # stop when the bracket is one step wide
    k1, k2 = 0.2 / (hi - lo), 2.0               # standard ITP hyper-parameters
    n_max = math.ceil(math.log2((hi - lo) / (2 * eps))) + n0
    j = 0
    while hi - lo > 1:
        x_half = (lo + hi) / 2
        r = eps * 2 ** (n_max - j) - (hi - lo) / 2
        delta = k1 * (hi - lo) ** k2
        if math.isinf(g_lo):
            x_f = x_half
        else:
            t_lo, t_hi = transform(domain[lo]), transform(domain[hi])
            x_f = to_index(t_hi - g_hi * (t_hi - t_lo) / (g_hi - g_lo))
            x_f = min(max(x_f, lo), hi)
        sgn = 1 if x_half >= x_f else -1
        x_t = x_f + sgn * delta if delta <= abs(x_half - x_f) else x_half
        x_itp = x_t if abs(x_t - x_half) <= r else x_half - sgn * r
        i = min(max(int(round(x_itp)), lo + 1), hi - 1)
        gi = g(i)
        if gi >= 0:
            hi, g_hi = i, gi
        else:
            lo, g_lo = i, gi
        j += 1
    return domain[hi]


class SigmaDomain:
    """0.5, 0.6, ..., 30.0 (the tool's sigma grid)."""
    def __len__(self): return 296
    def __getitem__(self, i): return round(0.5 + i / 10, 1)


class QDomain:
    """q from 2^18 down to 1024: lambda increases along it, so the smallest
    index meeting the target is the largest admissible q."""
    def __len__(self): return 2**18 - 1024 + 1
    def __getitem__(self, i): return 2**18 - i


SECANT = {
    "n":     lambda lam, t: secant_search(lam, range(64, 4097), t, float),
    "sigma": lambda lam, t: secant_search(lam, SigmaDomain(), t, math.log),
    "q":     lambda lam, t: secant_search(lam, QDomain(), t, lambda q: -math.log(q)),
    "k":     lambda lam, t: secant_search(lam, range(1, 17), t, float),
}
ITP = {
    "n":     lambda lam, t: itp_search(lam, range(64, 4097), t, float, lambda v: v - 64),
    "sigma": lambda lam, t: itp_search(lam, SigmaDomain(), t, math.log,
                                       lambda v: (math.exp(v) - 0.5) * 10),
    "q":     lambda lam, t: itp_search(lam, QDomain(), t, lambda q: -math.log(q),
                                       lambda v: 2**18 - math.exp(-v)),
    "k":     lambda lam, t: itp_search(lam, range(1, 17), t, float, lambda v: v - 1),
}
TOOL = {"n": tool_find_n, "sigma": tool_find_sigma, "q": tool_find_q, "k": tool_find_k}
TARGET_STEP = {"n": 4, "sigma": 4, "q": 4, "k": 8}


def targets_for(param, oracle):
    # finite values only (the estimator saturates to inf for huge instances), and only
    # cryptographically relevant targets (<= 300 bits)
    # from the fixed grid only (not live points), so the target list is stable across runs
    vals = [r["lambda"] for r in map(json.loads, (GRIDS / f"{param}.jsonl").read_text().splitlines())
            if r["lambda"] is not None and math.isfinite(r["lambda"])]
    lo, hi = math.ceil(min(vals)) + 1, min(math.floor(max(vals)) - 1, 300)
    step = TARGET_STEP[param]
    return list(range(lo + (-lo) % step, hi + 1, step))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("param", choices=list(TOOL))
    ap.add_argument("--shard", default="0/1")
    args = ap.parse_args()
    i, n_shards = map(int, args.shard.split("/"))
    OUT.mkdir(parents=True, exist_ok=True)

    suffix = f".{i}" if n_shards > 1 else ""
    oracle = Oracle(args.param, GRIDS / f"{args.param}.live{suffix}.jsonl")
    targets = targets_for(args.param, oracle)[i::n_shards]
    out = OUT / f"{args.param}{suffix}.jsonl"
    done = set()
    if out.exists():
        done = {(r["target"], r["algo"]) for r in map(json.loads, out.read_text().splitlines())}

    with open(out, "a") as fh:
        for t in targets:
            for algo, fn in (("tool_binary", TOOL[args.param]), ("secant", SECANT[args.param]),
                             ("itp", ITP[args.param])):
                if (t, algo) in done:
                    continue
                oracle.reset()
                ans = fn(oracle, t)
                rec = {"param": args.param, "target": t, "algo": algo, "answer": ans,
                       "calls": oracle.calls, "distinct": len(oracle.seen)}
                if ans is not None:   # local optimality: answer meets target, next step does not
                    nxt = {"n": ans - 1, "sigma": round(ans - 0.1, 1), "q": ans + 1, "k": ans - 1}[args.param]
                    saved = oracle.calls
                    rec["lam_answer"] = oracle(ans)
                    rec["lam_next"] = oracle(nxt) if nxt >= {"n": 64, "sigma": 0.5, "q": 1024, "k": 1}[args.param] and nxt <= {"n": 4096, "sigma": 30.0, "q": 2**18, "k": 16}[args.param] else None
                    oracle.calls = saved
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                print(json.dumps(rec), flush=True)


if __name__ == "__main__":
    main()
