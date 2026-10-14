# Lattice Security Estimator

A web tool for estimating the concrete security (λ, in bits) of lattice-based
parameter sets — LWE, RLWE and MLWE — built on the
[lattice-estimator](https://github.com/malb/lattice-estimator), plus the code
and data of the accompanying paper:

> **Moving Targets in Lattice Security Estimation: Version Drift and Search
> Reliability, with an Open Web Tool** — [paper/main.pdf](paper/main.pdf)

**Live tool:** <https://wejadstudio.com/estimator/>

The tool has two functions:

- **Estimate** — runs the primal uSVP, primal BDD and dual hybrid attacks on one
  parameter set and reports λ, the cost of the cheapest one.
- **Find parameter** — given a target λ, searches for the smallest `n`, `σ` or
  `k`, or the largest `q`, that still reaches it.

## Repository layout

```
backend/    FastAPI service; every estimate runs in a SageMath subprocess
frontend/   React + TypeScript + Vite user interface
paper/      the paper (LaTeX), its figures, raw data and experiment scripts
```

### Architecture

```
React frontend ──HTTP──> FastAPI (backend/app) ──subprocess──> Sage worker (backend/sage_worker) ──> lattice-estimator
```

lattice-estimator only runs inside SageMath, so the backend starts a Sage
process per request, which prints its result as a single JSON line.

## Running the tool

### Backend with Docker (recommended)

```bash
cd backend
cp .env.example .env          # set ALLOWED_ORIGINS for your frontend
docker compose up --build     # serves the API on port 8000
```

The image installs SageMath and checks out lattice-estimator at a **pinned
commit** (`3e48ef4`). The paper shows why: λ for the same parameters changes by
up to 13.8 bits between estimator versions.

### Backend without Docker

Requires a SageMath installation and a local checkout of lattice-estimator.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set SAGE_BIN and ESTIMATOR_PATH
uvicorn app.main:app --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                                         # http://localhost:5173
VITE_API_BASE_URL="https://your-backend" npm run build   # production build in dist/
```

The backend URL is baked in at build time (`VITE_API_BASE_URL`, default
`http://localhost:8000`).

### API

```bash
curl -s -X POST http://localhost:8000/estimate \
  -H 'Content-Type: application/json' \
  -d '{"scheme":"MLWE","n":256,"k":2,"q":3329,"eta":3,"secret_distribution":"centred_binomial"}'
```

Other endpoints: `POST /find-parameter`, `GET /presets`, `GET /health`.

## Reproducing the paper

All experiments were run with SageMath 10.5. Raw results are in
[paper/data/](paper/data/); the figures and tables are generated from them.

```bash
cd paper/experiments
export SAGE_BIN=/path/to/sage       # defaults to `sage` on the PATH
./setup_versions.sh                 # clone lattice-estimator + 13 version checkouts

python3 version_study.py            # E1: 12 versions x 14 parameter sets
python3 grid_study.py               # E2: dense lambda grids over n, sigma, q, k
$SAGE_BIN search_study.py n         # E2: replay searches (also: sigma, q, k)

# figures and tables (needs matplotlib, e.g. Sage's own python)
python3 analyze_versions.py         # figures/drift.pdf
python3 analyze_search.py           # figures/grids.pdf, data/search_table.tex
```

The full grid and search runs take several hours on a laptop. Every script is
resumable: rerunning it skips results already in `paper/data/`.
`bisect_test.sh` is the helper used with `git bisect run` to find the two
commits behind the version drift.

To build the paper:

```bash
cd paper && latexmk -pdf main.tex
```

## Modelling notes

- MLWE of rank `k` is estimated as LWE of dimension `n·k`.
- RLWE is estimated as LWE of dimension `n`; no ring-specific speed-ups are modelled.
- The number of samples defaults to unlimited (`m = ∞`).
- Only the three attacks above are run; the estimator implements more.

See the paper's limitations section for details.
