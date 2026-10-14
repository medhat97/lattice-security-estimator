"""
Runs inside SageMath. Binary-searches for the parameter that achieves
a target lambda. Entire search runs in one Sage process — fast.
"""
import sys
import json
import math
import os

ESTIMATOR_PATH = os.environ.get(
    "ESTIMATOR_PATH",
    "/home/crc-user/Downloads/master-degree/my-master/implementations/Cryptanlaysis/lattice-estimator",
)
sys.path.insert(0, ESTIMATOR_PATH)
from estimator import *  # noqa


# ── distribution helpers (same logic as worker.py) ───────────────────────────

def build_secret_dist(secret_distribution, eta=None):
    sd = secret_distribution.lower()
    if sd == "centred_binomial":
        if eta is None:
            raise ValueError("eta required for centred_binomial")
        return ND.CenteredBinomial(eta)
    if sd == "binary":
        return ND.Binary
    if sd == "gaussian":
        return None  # caller uses same as Xe
    return ND.Ternary  # ternary / uniform / default


def build_error_dist(sigma=None, q=None, alpha=None, eta=None, secret_distribution="ternary"):
    if secret_distribution.lower() == "centred_binomial":
        return ND.CenteredBinomial(eta)
    if sigma is not None and sigma > 0:
        return ND.DiscreteGaussian(float(sigma))
    if alpha is not None and alpha > 0:
        return ND.DiscreteGaussian(float(alpha) * float(q))
    raise ValueError("sigma or alpha required")


def build_params(n, q, sigma, alpha, eta, secret_distribution, m, scheme, k):
    effective_n = n * int(k) if scheme == "MLWE" else n
    sd = secret_distribution.lower()

    Xs = build_secret_dist(sd, eta=eta)
    Xe = build_error_dist(sigma=sigma, q=q, alpha=alpha, eta=eta, secret_distribution=sd)
    if Xs is None:
        Xs = Xe  # gaussian secret = same as error

    kwargs = dict(n=effective_n, q=q, Xs=Xs, Xe=Xe)
    if m is not None:
        kwargs["m"] = int(m)
    return LWE.Parameters(**kwargs)


def get_lambda(lwe_params):
    """Run the three attacks and return the minimum log2(rop)."""
    best = None
    for attack in (LWE.primal_usvp, LWE.dual_hybrid, LWE.primal_bdd):
        try:
            r = attack(lwe_params)
            rop = float(r["rop"])
            val = math.log2(rop) if rop > 0 else None
            if val is not None and (best is None or val < best):
                best = val
        except Exception:
            pass
    return best


def estimate_for(n, q, sigma, alpha, eta, secret_distribution, m, scheme, k):
    try:
        p = build_params(n, q, sigma, alpha, eta, secret_distribution, m, scheme, k)
        return get_lambda(p)
    except Exception:
        return None


# ── per-parameter search ──────────────────────────────────────────────────────

def next_power_of_two(x):
    p = 1
    while p < x:
        p <<= 1
    return p


def find_n(target, scheme, q, sigma, alpha, eta, secret_distribution, m, k):
    """Find minimum n (rounded up to power-of-2 for RLWE/MLWE) that hits target."""
    ring = scheme in ("RLWE", "MLWE")
    lo, hi = 64, 4096

    def lam(n_val):
        n_use = next_power_of_two(n_val) if ring else n_val
        return estimate_for(n_use, q, sigma, alpha, eta, secret_distribution, m, scheme, k)

    # check feasibility
    if lam(hi) is None or lam(hi) < target:
        return None, None, None, "No solution found: even n=4096 does not reach target λ"

    result = hi
    while lo <= hi:
        mid = (lo + hi) // 2
        val = lam(mid)
        if val is not None and val >= target:
            result = mid
            hi = mid - 1
        else:
            lo = mid + 1

    n_found = next_power_of_two(result) if ring else result
    lam_found = lam(result)
    lam_below = lam(result - 1) if result > 64 else None
    return n_found, lam_found, lam_below, None


def find_k(target, scheme, n, q, sigma, alpha, eta, secret_distribution, m):
    """Find minimum k (module rank) for MLWE."""
    for k in range(1, 17):
        val = estimate_for(n, q, sigma, alpha, eta, secret_distribution, m, scheme, k)
        if val is not None and val >= target:
            lam_below = estimate_for(n, q, sigma, alpha, eta, secret_distribution, m, scheme, k - 1) if k > 1 else None
            return k, val, lam_below, None
    return None, None, None, "No solution found: even k=16 does not reach target λ"


def find_sigma(target, scheme, n, q, alpha, eta, secret_distribution, m, k):
    """Find minimum sigma using binary search (~10 iterations, fast)."""
    lo_s, hi_s = 0.5, 30.0  # practical sigma range for cryptographic schemes

    def lam(s):
        return estimate_for(n, q, round(s, 1), alpha, eta, secret_distribution, m, scheme, k)

    if lam(hi_s) is None or lam(hi_s) < target:
        return None, None, None, "No solution: even σ=30 does not reach target λ"

    # binary search: find minimum sigma where lambda >= target
    result = hi_s
    while hi_s - lo_s > 0.1:
        mid = (lo_s + hi_s) / 2
        val = lam(mid)
        if val is not None and val >= target:
            result = mid
            hi_s = mid
        else:
            lo_s = mid

    result = round(result, 1)
    lam_found = lam(result)
    prev_s = round(result - 0.1, 1) if result > 0.5 else None
    lam_below = lam(prev_s) if prev_s is not None else None
    return result, lam_found, lam_below, None


def find_q(target, scheme, n, sigma, alpha, eta, secret_distribution, m, k):
    """Find maximum q that still achieves target (larger q → less secure).
    Binary search over practical range [1024, 2^18] — ~18 iterations.
    """
    lo, hi = 1024, 2**18  # 262144 — covers all practical cryptographic q values

    def lam(q_val):
        return estimate_for(n, q_val, sigma, alpha, eta, secret_distribution, m, scheme, k)

    # feasibility: check hi end (largest q = least secure)
    if lam(hi) is not None and lam(hi) >= target:
        # even the largest q is still secure enough — return it as the maximum
        return hi, lam(hi), lam(hi + 1024), None

    # check lo end (smallest q = most secure)
    lam_lo = lam(lo)
    if lam_lo is None or lam_lo < target:
        return None, None, None, f"No solution: q={lo} (most secure in range) does not reach target λ={target}"

    result = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        val = lam(mid)
        if val is not None and val >= target:
            result = mid
            lo = mid + 1
        else:
            hi = mid - 1

    lam_found = lam(result)
    lam_above = lam(result + 256) if result + 256 <= 2**18 else None
    return result, lam_found, lam_above, None


# ── main ──────────────────────────────────────────────────────────────────────

def run(params_json):
    p = json.loads(params_json)

    target   = float(p["target_lambda"])
    find_param = p["find_param"]
    scheme   = p["scheme"].upper()
    known    = p.get("known", {})

    q     = known.get("q")
    n     = known.get("n")
    sigma = known.get("sigma")
    alpha = known.get("alpha")
    eta   = known.get("eta")
    m     = known.get("m")
    k     = known.get("k", 1)
    sd    = known.get("secret_distribution", "ternary")

    warnings = []
    if scheme == "RLWE":
        warnings.append("RLWE is estimated through an LWE-style model.")

    if find_param == "n":
        found, lam_found, lam_below, err = find_n(target, scheme, q, sigma, alpha, eta, sd, m, k)
        verify_label = "n − 1"
    elif find_param == "k":
        found, lam_found, lam_below, err = find_k(target, scheme, n, q, sigma, alpha, eta, sd, m)
        verify_label = "k − 1"
    elif find_param == "sigma":
        found, lam_found, lam_below, err = find_sigma(target, scheme, n, q, alpha, eta, sd, m, k)
        verify_label = "σ − 0.1"
    elif find_param == "q":
        found, lam_found, lam_below, err = find_q(target, scheme, n, sigma, alpha, eta, sd, m, k)
        verify_label = "q + 1"
    else:
        print(json.dumps({"error": f"Unknown find_param: {find_param}"}))
        return

    if err:
        print(json.dumps({"error": err, "warnings": warnings}))
        return

    complete = {**known, find_param: found, "scheme": scheme}

    output = {
        "found_param":  find_param,
        "found_value":  found,
        "verification": {
            # inf (estimator saturated) is not valid JSON, so report it as None
            "at_found":       round(lam_found, 2) if lam_found and math.isfinite(lam_found) else None,
            "at_step_below":  round(lam_below, 2) if lam_below and math.isfinite(lam_below) else None,
            "step_below_label": verify_label,
        },
        "parameters_complete": complete,
        "warnings": warnings,
    }
    print(json.dumps(output))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No parameters provided"}))
        sys.exit(1)
    run(sys.argv[1])
