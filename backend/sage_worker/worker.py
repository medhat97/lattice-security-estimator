"""
Runs inside SageMath. Called by estimator.py via subprocess.
Reads JSON params from argv[1], outputs JSON result to stdout.
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

from estimator import *  # noqa: F401,F403 — standard lattice-estimator import style


def cost_to_dict(cost):
    """Convert a lattice-estimator Cost object to a serialisable dict."""
    result = {}

    try:
        rop = float(cost["rop"])
        result["rop_log2"] = round(math.log2(rop), 2) if 0 < rop < math.inf else None
        if rop == math.inf:  # estimator saturated; inf is not valid JSON
            result["error"] = "Infinite cost: parameters are outside the estimator's range"
    except (KeyError, ValueError, TypeError):
        result["rop_log2"] = None

    for key in ("beta", "d", "m", "zeta"):
        try:
            result[key] = int(cost[key])
        except (KeyError, TypeError):
            pass

    try:
        result["tag"] = str(cost["tag"])
    except (KeyError, TypeError):
        pass

    return result


def build_secret_dist(secret_distribution, eta=None):
    # ND.Binary and ND.Ternary are pre-built singleton instances, not classes
    sd = secret_distribution.lower()
    if sd == "centred_binomial":
        if eta is None:
            raise ValueError("eta is required for centred_binomial secret distribution")
        return ND.CenteredBinomial(eta)
    if sd == "gaussian":
        # caller should pass sigma; we signal this so run_estimates reuses Xe
        return None
    if sd == "binary":
        return ND.Binary
    if sd == "uniform":
        return ND.Ternary   # fallback; uniform mod q needs q, use ternary as safe default
    return ND.Ternary       # default for "ternary" and unknown values


def build_error_dist(sigma, q, alpha=None):
    if sigma is not None and sigma > 0:
        return ND.DiscreteGaussian(float(sigma))
    if alpha is not None and alpha > 0:
        return ND.DiscreteGaussian(float(alpha) * float(q))
    raise ValueError("Either sigma or alpha must be provided for the error distribution")


def run_estimates(params_json):
    p = json.loads(params_json)

    scheme   = p["scheme"].upper()   # LWE | RLWE | MLWE
    n        = int(p["n"])
    q        = int(p["q"])
    sigma    = p.get("sigma")
    alpha    = p.get("alpha")
    m        = p.get("m")
    k        = p.get("k", 1)        # module rank for MLWE
    eta      = p.get("eta")
    secret_distribution = p.get("secret_distribution", "ternary")

    # For MLWE the effective LWE dimension is n * k
    effective_n = n * int(k) if scheme == "MLWE" else n

    Xs = build_secret_dist(secret_distribution, eta=eta)

    # Gaussian secret: same distribution as the error
    if Xs is None:
        Xs = build_error_dist(sigma, q, alpha)

    # For centred-binomial schemes (Kyber), Xe also uses eta
    if secret_distribution.lower() == "centred_binomial":
        Xe = ND.CenteredBinomial(eta)
    else:
        Xe = build_error_dist(sigma, q, alpha)

    lwe_kwargs = dict(n=effective_n, q=q, Xs=Xs, Xe=Xe)
    if m is not None:
        lwe_kwargs["m"] = int(m)   # omit m to use estimator default (oo)
    lwe_params = LWE.Parameters(**lwe_kwargs)

    attacks = {}
    warnings = []

    if scheme == "RLWE":
        warnings.append(
            "RLWE is estimated through an LWE-style model (effective_n = n). "
            "Ring-specific speedups are not modelled."
        )

    # Primal USVP
    try:
        res = LWE.primal_usvp(lwe_params)
        attacks["primal_usvp"] = cost_to_dict(res)
    except Exception as e:
        attacks["primal_usvp"] = {"error": str(e)}

    # Dual hybrid
    try:
        res = LWE.dual_hybrid(lwe_params)
        attacks["dual_hybrid"] = cost_to_dict(res)
    except Exception as e:
        attacks["dual_hybrid"] = {"error": str(e)}

    # Primal BDD (often dominated by usvp but informative)
    try:
        res = LWE.primal_bdd(lwe_params)
        attacks["primal_bdd"] = cost_to_dict(res)
    except Exception as e:
        attacks["primal_bdd"] = {"error": str(e)}

    # Compute lambda as the minimum rop_log2 across all successful attacks
    valid_costs = {
        name: a["rop_log2"]
        for name, a in attacks.items()
        if "rop_log2" in a and a["rop_log2"] is not None
    }

    if not valid_costs:
        saturated = all(a.get("error", "").startswith("Infinite cost") for a in attacks.values())
        msg = ("All attacks report infinite cost: parameters are outside the estimator's range"
               if saturated else "All attacks failed")
        output = {"error": msg, "warnings": warnings}
    else:
        dominant = min(valid_costs, key=valid_costs.get)
        output = {
            "lambda_bits": round(valid_costs[dominant], 2),
            "dominant_attack": dominant,
            "attacks": attacks,
            "effective_n": effective_n,
            "warnings": warnings,
        }

    print(json.dumps(output))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No parameters provided"}))
        sys.exit(1)
    run_estimates(sys.argv[1])
