"""
Analyse experiment 1 (version drift): summary table + figure.

Run with the Sage env's python (has matplotlib):
  /home/crc-user/miniconda3/envs/sage-env/bin/python3 analyze_versions.py
Writes ../figures/drift.pdf and ../data/drift_summary.json, prints a summary.
"""
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from plotstyle import apply_style, SERIES, MARKERS, LINESTYLES, INK_2  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
FIG = HERE.parent / "figures"

ATTACK_SHORT = {"primal_usvp": "uSVP", "primal_bdd": "BDD", "dual_hybrid": "dual"}
GROUPS = [("Kyber", ["Kyber-512", "Kyber-768", "Kyber-1024"]),
          ("FrodoKEM", ["Frodo-640", "Frodo-976"]),
          ("NewHope", ["NewHope-512", "NewHope-1024"])]
DEPLOYED, LAPTOP = "3e48ef4", "a51a410"


def load():
    rows = [json.loads(l) for l in (DATA / "version_study.jsonl").read_text().splitlines()]
    by = defaultdict(dict)  # (family, scheme) -> version -> row
    for r in rows:
        by[(r["family"], r["scheme"])][r["version"]] = r
    return rows, by


def dominant(r):
    vals = {k: a["rop_log2"] for k, a in r["attacks"].items() if a.get("rop_log2") is not None}
    return min(vals, key=vals.get) if vals else None


def main():
    rows, by = load()
    versions = sorted({(r["date"], r["version"]) for r in rows})
    vorder = [v for _, v in versions]
    vdate = {v: date.fromisoformat(d) for d, v in versions}

    summary = {}
    for (fam, sch), per in sorted(by.items()):
        seq = [(v, per[v]) for v in vorder if v in per and per[v].get("lambda") is not None]
        if not seq:
            continue
        lams = [r["lambda"] for _, r in seq]
        doms = [dominant(r) for _, r in seq]
        steps = [(seq[i][0], seq[i + 1][0], lams[i + 1] - lams[i]) for i in range(len(seq) - 1)]
        big = max(steps, key=lambda s: abs(s[2])) if steps else None
        summary[f"{fam}:{sch}"] = {
            "first": (seq[0][0], lams[0]), "last": (seq[-1][0], lams[-1]),
            "min": min(lams), "max": max(lams), "range": max(lams) - min(lams),
            "net": lams[-1] - lams[0],
            "dominant_first": doms[0], "dominant_last": doms[-1],
            "dominant_changes": sum(doms[i] != doms[i + 1] for i in range(len(doms) - 1)),
            "largest_step": big,
            "laptop_vs_deployed": (per[LAPTOP]["lambda"] - per[DEPLOYED]["lambda"])
            if LAPTOP in per and DEPLOYED in per else None,
            "n_versions": len(seq),
        }

    # tool mapping (m = inf) vs reference (finite m), per version
    gaps = {}
    for (fam, sch), per in by.items():
        if fam != "tool" or ("ref", sch) not in by:
            continue
        ref = by[("ref", sch)]
        g = [per[v]["lambda"] - ref[v]["lambda"] for v in vorder
             if v in per and v in ref and per[v].get("lambda") and ref[v].get("lambda")]
        if g:
            gaps[sch] = {"min": min(g), "max": max(g), "at_deployed":
                         per[DEPLOYED]["lambda"] - ref[DEPLOYED]["lambda"]
                         if DEPLOYED in per and DEPLOYED in ref else None}
    (DATA / "drift_summary.json").write_text(json.dumps(
        {"summary": summary, "tool_minus_ref": gaps, "versions": versions}, indent=1))

    for k, s in summary.items():
        print(f"{k:22s} {s['first'][1]:7.2f} -> {s['last'][1]:7.2f}  net {s['net']:+6.2f}  "
              f"range {s['range']:5.2f}  dom {s['dominant_first']}->{s['dominant_last']} "
              f"({s['dominant_changes']} changes)  laptop-deployed "
              f"{s['laptop_vs_deployed'] if s['laptop_vs_deployed'] is None else round(s['laptop_vs_deployed'], 2)}")
    for k, g in gaps.items():
        print(f"tool-ref {k:14s} min {g['min']:+6.2f} max {g['max']:+6.2f} deployed {g['at_deployed']}")

    # ── figure: one panel per scheme family, reference sets, change vs. Dec 2021 ──
    apply_style()
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.0), sharex=True, sharey=True)
    for ax, (title, schemes) in zip(axes, GROUPS):
        ax.axhline(0, color=INK_2, lw=0.6)
        ends = []
        for i, sch in enumerate(schemes):
            per = by.get(("ref", sch), {})
            vs = [v for v in vorder if v in per and per[v].get("lambda") is not None]
            if not vs:
                continue
            base = per[vs[0]]["lambda"]
            xs = [vdate[v] for v in vs]
            ys = [per[v]["lambda"] - base for v in vs]
            ax.step(xs, ys, where="post", color=SERIES[i], lw=1.5, ls=LINESTYLES[i],
                    label=sch.split("-")[1])
            for x, y, v in zip(xs, ys, vs):   # filled = primal BDD cheapest, hollow = dual hybrid
                hollow = dominant(per[v]) == "dual_hybrid"
                ax.plot([x], [y], ls="none", marker=MARKERS[i], ms=3.8, color=SERIES[i],
                        mfc="white" if hollow else SERIES[i], mec=SERIES[i], mew=0.9)
            ends.append((ys[-1], sch.split("-")[1], xs[-1]))
        # direct end labels, pushed apart when two lines end within ~1 bit
        ends.sort()
        for j, (y, lab, x) in enumerate(ends):
            close = any(abs(y - y2) < 1.2 for k, (y2, _, _) in enumerate(ends) if k != j)
            dy = (-4 if j == 0 else 4) if close else 0
            ax.annotate(lab, (x, y), xytext=(4, dy), textcoords="offset points",
                        fontsize=6.5, color=INK_2, va="center")
        if DEPLOYED in vdate:
            ax.axvline(vdate[DEPLOYED], color=INK_2, lw=0.6, ls=(0, (2, 2)))
        ax.set_title(title)
        ax.legend(loc="lower left", handlelength=2.2)
        ax.xaxis.set_major_locator(matplotlib.dates.YearLocator())
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
    axes[0].set_ylabel(r"$\Delta\lambda$ vs. Dec. 2021 (bits)")
    axes[-1].annotate("deployed", (vdate[DEPLOYED], axes[-1].get_ylim()[1]), xytext=(-2, -2),
                      textcoords="offset points", ha="right", va="top", fontsize=6.3, color=INK_2)
    fig.tight_layout(pad=0.3, w_pad=0.8)
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / "drift.pdf")
    print("wrote", FIG / "drift.pdf")


if __name__ == "__main__":
    main()
