"""
Analyse experiment 2: monotonicity of lambda on the grids, and the replayed
searches (tool binary search vs. safeguarded secant).

Run with the Sage env's python (has matplotlib):
  /home/crc-user/miniconda3/envs/sage-env/bin/python3 analyze_search.py
Writes ../figures/grids.pdf and ../data/search_summary.json, prints a summary.
"""
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from plotstyle import apply_style, SERIES, MARKERS, LINESTYLES, INK_2  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
FIG = HERE.parent / "figures"
DIRECTION = {"n": +1, "sigma": +1, "q": -1, "k": +1}   # sign of d(lambda)/dx expected
ATTACKS = [("primal_usvp", "primal uSVP"), ("primal_bdd", "primal BDD"), ("dual_hybrid", "dual hybrid")]


def load_grid(g):
    rows = [json.loads(l) for l in (DATA / "grids" / f"{g}.jsonl").read_text().splitlines()]
    return sorted(rows, key=lambda r: r["x"])


def monotonicity(g):
    rows = load_grid(g)
    pts = [(r["x"], r["lambda"]) for r in rows if r["lambda"] is not None and math.isfinite(r["lambda"])]
    viol = [(a[0], b[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])
            if (b[1] - a[1]) * DIRECTION[g] < 0]
    # a real-valued target t is ambiguous if the admissible set {x: lambda(x) >= t}
    # is not one interval reaching the strong end of the range; this happens exactly
    # when t lies inside a dip, so measure the union of dip intervals.
    ys = [y for _, y in pts]
    if DIRECTION[g] < 0:
        ys = ys[::-1]
    intervals, run_max = [], -math.inf
    for y in ys:                      # walking towards stronger parameters
        if y < run_max:
            intervals.append((y, run_max))
        run_max = max(run_max, y)
    covered, cur = 0.0, None          # length of the union of (lo, hi] intervals
    for lo, hi in sorted(intervals):
        if cur is None or lo > cur[1]:
            if cur:
                covered += cur[1] - cur[0]
            cur = [lo, hi]
        else:
            cur[1] = max(cur[1], hi)
    if cur:
        covered += cur[1] - cur[0]
    span = max(ys) - min(ys)
    n_inf = sum(1 for r in rows if r["lambda"] is not None and not math.isfinite(r["lambda"]))
    return {"points": len(rows), "pairs": len(pts) - 1, "violations": len(viol),
            "worst_drop": min((abs(v[2]) * -1 for v in viol), default=0.0),
            "worst": sorted(viol, key=lambda v: -abs(v[2]))[:3],
            "ambiguous_target_fraction": covered / span if span else 0.0,
            "lambda_range": (min(ys), max(ys)), "infinite_points": n_inf}


def truth(g, t):
    """Smallest admissible value on the grid (largest for q): ground truth for the
    full-resolution grids n, sigma, k. None if the grid does not contain it."""
    pts = [(r["x"], r["lambda"]) for r in load_grid(g) if r["lambda"] is not None]
    ok = [x for x, y in pts if y >= t]
    if not ok:
        return None
    return max(ok) if g == "q" else min(ok)


TARGET_STEP = {"n": 4, "sigma": 4, "q": 4, "k": 8}


def targets(g):
    """Same rule as search_study.targets_for: finite grid values, targets <= 300 bits."""
    vals = [r["lambda"] for r in load_grid(g) if r["lambda"] is not None and math.isfinite(r["lambda"])]
    lo, hi = math.ceil(min(vals)) + 1, min(math.floor(max(vals)) - 1, 300)
    step = TARGET_STEP[g]
    return set(range(lo + (-lo) % step, hi + 1, step))


def search_summary():
    out = {}
    for g in ("n", "sigma", "q", "k"):
        recs, keep = [], targets(g)
        for f in (DATA / "search").glob(f"{g}*.jsonl"):
            recs += [r for r in map(json.loads, f.read_text().splitlines()) if r["target"] in keep]
        if not recs:
            continue
        per = {}
        for algo in ("tool_binary", "secant", "itp"):
            rs = [r for r in recs if r["algo"] == algo and r["answer"] is not None]
            if not rs:
                continue
            local_ok = sum(1 for r in rs if r["lam_answer"] >= r["target"] and
                           (r["lam_next"] is None or r["lam_next"] < r["target"]))
            exact = None
            if g != "q":  # full-resolution grid: compare with the true optimum
                exact = sum(1 for r in rs if truth(g, r["target"]) == r["answer"])
            calls = [r["calls"] for r in rs]
            per[algo] = {"targets": len(rs), "calls_mean": sum(calls) / len(calls),
                         "calls_min": min(calls), "calls_max": max(calls),
                         "local_ok": local_ok, "exact": exact}
        # does each algorithm return the same answer as the tool for the same target?
        tool = {r["target"]: r["answer"] for r in recs if r["algo"] == "tool_binary"}
        for algo in ("secant", "itp"):
            other = {r["target"]: r["answer"] for r in recs if r["algo"] == algo}
            both = set(tool) & set(other)
            per[f"agree_{algo}"] = f"{sum(1 for t in both if tool[t] == other[t])}/{len(both)}"
            if "tool_binary" in per and algo in per:
                per[f"saving_{algo}"] = 1 - per[algo]["calls_mean"] / per["tool_binary"]["calls_mean"]
        out[g] = per
    return out


def seconds_per_call():
    tot, n = 0.0, 0
    for g in ("n", "sigma", "q", "k"):
        for r in load_grid(g):
            tot += sum(a.get("seconds", 0) for a in r["attacks"].values())
            n += 1
    return tot / n


def figure():
    apply_style()
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.05))

    def per_attack(ax, g, xform=lambda x: x, cap=None):
        rows = load_grid(g)
        for i, (key, label) in enumerate(ATTACKS):
            xs, ys = [], []
            for r in rows:
                v = r["attacks"][key].get("rop_log2")
                if v is None or not math.isfinite(v):
                    continue
                xs.append(xform(r["x"]))
                ys.append(v)
            ax.plot(xs, ys, color=SERIES[i], ls=LINESTYLES[i], lw=1.2, label=label)
        return rows

    # (a) n: per-attack curves, lambda = their minimum
    per_attack(axes[0], "n")
    axes[0].set_xlabel(r"LWE dimension $n$ ($q=3329$, CBD(2))")
    axes[0].set_ylabel(r"$\log_2$ cost (bits)")
    axes[0].set_title("(a) dimension")
    axes[0].legend(loc="upper left", handlelength=2.2)

    # (b) sigma, log x
    per_attack(axes[1], "sigma")
    axes[1].set_xscale("log")
    axes[1].set_xlabel(r"$\sigma$ ($n=640$, $q=2^{15}$)")
    axes[1].set_title(r"(b) noise width")

    # (c) k: per-attack, infinite costs drawn as markers at the top edge
    rows = per_attack(axes[2], "k")
    top = 1000
    for i, (key, _) in enumerate(ATTACKS):
        ks = [r["x"] for r in rows if r["attacks"][key].get("rop_log2") is not None
              and not math.isfinite(r["attacks"][key]["rop_log2"])]
        axes[2].plot(ks, [top - 25 * i] * len(ks), ls="none", marker=MARKERS[i], ms=3.2,
                     color=SERIES[i], mfc="white", mew=0.9)
    for r in rows:   # plot each attack's finite values as markers too (few points)
        for i, (key, _) in enumerate(ATTACKS):
            v = r["attacks"][key].get("rop_log2")
            if v is not None and math.isfinite(v):
                axes[2].plot([r["x"]], [v], ls="none", marker=MARKERS[i], ms=2.8, color=SERIES[i])
    axes[2].axhline(256, color=INK_2, lw=0.6, ls=(0, (2, 2)))
    axes[2].annotate(r"$\lambda=256$", (16, 256), xytext=(0, 2), textcoords="offset points",
                     ha="right", va="bottom", fontsize=6.3, color=INK_2)
    axes[2].annotate(r"$\infty$ (saturated)", (16, top), xytext=(0, 5), textcoords="offset points",
                     ha="right", va="bottom", fontsize=6.3, color=INK_2)
    axes[2].set_ylim(0, top + 70)
    axes[2].set_xlabel(r"module rank $k$ ($n=256$, $q=3329$)")
    axes[2].set_title("(c) module rank")
    fig.tight_layout(pad=0.3, w_pad=0.9)
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / "grids.pdf")


def write_table(srch):
    """LaTeX rows for Table III (search cost), generated so numbers are never hand-copied."""
    names = {"n": "$n$", "sigma": r"$\sigma$", "q": "$q$", "k": "$k$"}
    lines = []
    for g in ("n", "sigma", "q", "k"):
        s = srch.get(g)
        if not s or not all(a in s for a in ("tool_binary", "secant", "itp")):
            continue
        b, c, i = s["tool_binary"], s["secant"], s["itp"]
        ok = all(x.split("/")[0] == x.split("/")[1] for x in (s["agree_secant"], s["agree_itp"]))
        lines.append(
            f"{names[g]} & {b['targets']} & {b['calls_mean']:.1f} & {b['calls_max']} & "
            f"{c['calls_mean']:.1f} & {c['calls_max']} & {i['calls_mean']:.1f} & {i['calls_max']} & "
            f"${100 * s['saving_itp']:+.0f}\\%$ & {'yes' if ok else 'NO'} \\\\")
    (DATA / "search_table.tex").write_text("\n".join(lines) + "\n")


def main():
    mono = {g: monotonicity(g) for g in ("n", "sigma", "q", "k")}
    srch = search_summary()
    spc = seconds_per_call()
    (DATA / "search_summary.json").write_text(json.dumps(
        {"monotonicity": mono, "search": srch, "seconds_per_call": spc}, indent=1, default=str))
    for g, m in mono.items():
        print(f"{g:6s} pts {m['points']:4d} viol {m['violations']}/{m['pairs']} worst {m['worst']} "
              f"ambiguous {100 * m['ambiguous_target_fraction']:.3f}% inf {m['infinite_points']}")
    for g, s in srch.items():
        print(g, json.dumps(s))
    print(f"mean seconds per estimator call: {spc:.1f}")
    write_table(srch)
    figure()
    print("wrote", FIG / "grids.pdf")


if __name__ == "__main__":
    main()
