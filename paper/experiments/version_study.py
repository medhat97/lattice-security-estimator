"""
Experiment 1: how much does lambda for fixed parameter sets drift across
lattice-estimator versions?

Runs every parameter set below against every checkout in versions/ and
appends one JSON line per (version, set) to ../data/version_study.jsonl.
Resumable: (version, label) pairs already in the file are skipped.

Usage: python3 version_study.py [--jobs 6]
"""
import argparse
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAGE = os.environ.get("SAGE_BIN", "sage")   # path to the sage executable
OUT = HERE.parent / "data" / "version_study.jsonl"
REPO = HERE / "estimator-repo"

# Snapshots: last commit before each half-year boundary, plus the laptop
# copy (a51a410), the deployed VPS copy (3e48ef4) and upstream HEAD (53da598).
VERSIONS = ["4be104e", "f9dc7c6", "6a96c61", "cf36315", "c2d5fe9", "dfbc622",
            "374f073", "5ba00f5", "a2be406", "a51a410", "3e48ef4", "53da598"]


def cbd(e): return {"type": "cbd", "param": e}
def gauss(s): return {"type": "gauss", "param": s}
TERN = {"type": "ternary"}

# "ref": lattice-estimator's own schemes.py definitions (finite m), held fixed.
# "tool": exactly how the web tool maps its presets (m = infinity).
# "nh-ref": NewHope with its specified CBD(8) secret and error, m = n.
SETS = [
    ("ref",  "Kyber-512",    dict(n=512,  q=3329,  xs=cbd(3),     xe=cbd(3),     m=512)),
    ("ref",  "Kyber-768",    dict(n=768,  q=3329,  xs=cbd(2),     xe=cbd(2),     m=768)),
    ("ref",  "Kyber-1024",   dict(n=1024, q=3329,  xs=cbd(2),     xe=cbd(2),     m=1024)),
    ("ref",  "Frodo-640",    dict(n=640,  q=2**15, xs=gauss(2.8), xe=gauss(2.8), m=656)),
    ("ref",  "Frodo-976",    dict(n=976,  q=2**16, xs=gauss(2.3), xe=gauss(2.3), m=992)),
    ("ref",  "NewHope-512",  dict(n=512,  q=12289, xs=cbd(8),     xe=cbd(8),     m=512)),
    ("ref",  "NewHope-1024", dict(n=1024, q=12289, xs=cbd(8),     xe=cbd(8),     m=1024)),
    ("tool", "Kyber-512",    dict(n=512,  q=3329,  xs=cbd(3),     xe=cbd(3),     m=None)),
    ("tool", "Kyber-768",    dict(n=768,  q=3329,  xs=cbd(2),     xe=cbd(2),     m=None)),
    ("tool", "Kyber-1024",   dict(n=1024, q=3329,  xs=cbd(2),     xe=cbd(2),     m=None)),
    ("tool", "Frodo-640",    dict(n=640,  q=2**15, xs=gauss(2.8), xe=gauss(2.8), m=None)),
    ("tool", "Frodo-976",    dict(n=976,  q=2**16, xs=gauss(2.3), xe=gauss(2.3), m=None)),
    ("tool", "NewHope-512",  dict(n=512,  q=12289, xs=TERN,       xe=gauss(3.4), m=None)),
    ("tool", "NewHope-1024", dict(n=1024, q=12289, xs=TERN,       xe=gauss(3.4), m=None)),
]


def commit_date(h):
    return subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%cd",
                           "--date=short", h], capture_output=True, text=True).stdout.strip()


def run(job):
    version, family, name, spec = job
    spec = dict(spec, label=f"{family}:{name}")
    try:
        p = subprocess.run([SAGE, str(HERE / "run_point.py"), str(HERE / "versions" / version),
                            json.dumps(spec)], capture_output=True, text=True, timeout=3600)
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception as e:
        res = {"error": f"{type(e).__name__}: {e}"[:300], "attacks": {}, "lambda": None}
    res.update(version=version, date=commit_date(version), family=family, scheme=name,
               params={k: v for k, v in spec.items() if k != "label"})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()

    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            r = json.loads(line)
            done.add((r["version"], r["family"], r["scheme"]))

    jobs = [(v, f, n, s) for v in VERSIONS for f, n, s in SETS if (v, f, n) not in done]
    print(f"{len(jobs)} jobs to run ({len(done)} already done)", flush=True)
    with ThreadPoolExecutor(args.jobs) as ex, OUT.open("a") as fh:
        for i, res in enumerate(ex.map(run, jobs), 1):
            fh.write(json.dumps(res) + "\n")
            fh.flush()
            lam = res.get("lambda")
            print(f"[{i}/{len(jobs)}] {res['version']} {res['family']}:{res['scheme']} "
                  f"lambda={lam if lam is None else round(lam, 2)}", flush=True)


if __name__ == "__main__":
    main()
