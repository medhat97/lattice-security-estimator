"""
Experiment 2 (data collection): dense lambda grids over each parameter the
tool's "Find parameter" feature searches (n, sigma, q, k), using the
lattice-estimator version deployed on the live site (3e48ef4) and the tool's
own LWE mapping (m = infinity).

Writes ../data/grids/<grid>.jsonl. Resumable.
Usage: python3 grid_study.py [--jobs 6] [--grids n,sigma,q,k,repeat]
"""
import argparse
import json
import os
import math
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAGE = os.environ.get("SAGE_BIN", "sage")   # path to the sage executable
VERSION = "3e48ef4"
DATA = HERE.parent / "data" / "grids"


def cbd(e): return {"type": "cbd", "param": e}
def gauss(s): return {"type": "gauss", "param": s}


def grid_specs(name):
    if name == "n":  # Kyber-like plain LWE, every integer n
        return [dict(key=f"n={n}", x=n, n=n, q=3329, xs=cbd(2), xe=cbd(2), m=None)
                for n in range(256, 1025)]
    if name == "sigma":  # Frodo-640-like, the tool's 0.1 sigma grid over [0.5, 30]
        return [dict(key=f"sigma={s / 10:.1f}", x=s / 10, n=640, q=2**15,
                     xs=gauss(s / 10), xe=gauss(s / 10), m=None) for s in range(5, 301)]
    if name == "q":  # Frodo-640-like; log-spaced over the tool's range + 3 dense windows
        lo, hi, pts = 1024, 2**18, 200
        qs = {round(lo * (hi / lo) ** (i / (pts - 1))) for i in range(pts)}
        for c in (4096, 32768, 131072):
            qs.update(range(c - 16, c + 16))
        return [dict(key=f"q={q}", x=q, n=640, q=q, xs=gauss(2.8), xe=gauss(2.8), m=None)
                for q in sorted(qs)]
    if name == "k":  # MLWE n=256, q=3329, CBD(2): effective dimension 256k
        return [dict(key=f"k={k}", x=k, n=256 * k, q=3329, xs=cbd(2), xe=cbd(2), m=None)
                for k in range(1, 17)]
    if name == "repeat":  # determinism check: re-evaluate points from the n grid
        return [dict(key=f"n={n}#rep", x=n, n=n, q=3329, xs=cbd(2), xe=cbd(2), m=None)
                for n in range(300, 1025, 50)]
    raise ValueError(name)


def run_chunk(args):
    spec_file, out_file = args
    subprocess.run([SAGE, str(HERE / "run_batch.py"), str(HERE / "versions" / VERSION),
                    str(spec_file), str(out_file)], check=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--grids", default="n,sigma,q,k,repeat")
    args = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)

    chunks = []
    for g in args.grids.split(","):
        specs = grid_specs(g)
        (DATA / f"{g}.specs.jsonl").write_text("".join(json.dumps(s) + "\n" for s in specs))
        nchunks = min(args.jobs, len(specs))
        for c in range(nchunks):  # interleave so chunks have similar cost
            part = specs[c::nchunks]
            sf = DATA / f"{g}.chunk{c}.specs.jsonl"
            sf.write_text("".join(json.dumps(s) + "\n" for s in part))
            chunks.append((sf, DATA / f"{g}.chunk{c}.out.jsonl"))

    with ThreadPoolExecutor(args.jobs) as ex:
        list(ex.map(run_chunk, chunks))

    # merge chunk outputs into one file per grid, ordered by x
    for g in args.grids.split(","):
        specs = {json.loads(l)["key"]: json.loads(l) for l in
                 (DATA / f"{g}.specs.jsonl").read_text().splitlines()}
        rows = []
        for f in DATA.glob(f"{g}.chunk*.out.jsonl"):
            for line in f.read_text().splitlines():
                r = json.loads(line)
                r["x"] = specs[r["key"]]["x"]
                rows.append(r)
        rows.sort(key=lambda r: r["x"])
        (DATA / f"{g}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        print(f"{g}: {len(rows)}/{len(specs)} points", flush=True)


if __name__ == "__main__":
    main()
