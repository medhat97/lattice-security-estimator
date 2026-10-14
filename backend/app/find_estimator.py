import json
import os
import subprocess
from pathlib import Path

SAGE_BIN = os.environ.get("SAGE_BIN", "/home/crc-user/miniconda3/envs/sage-env/bin/sage")
WORKER_SCRIPT = Path(__file__).resolve().parent.parent / "sage_worker" / "find_worker.py"
ESTIMATOR_PATH = os.environ.get(
    "ESTIMATOR_PATH",
    "/home/crc-user/Downloads/master-degree/my-master/implementations/Cryptanlaysis/lattice-estimator",
)
TIMEOUT_SECONDS = int(os.environ.get("ESTIMATOR_TIMEOUT", "300"))


def run_find(params: dict) -> dict:
    params_json = json.dumps(params)
    env = os.environ.copy()
    env["ESTIMATOR_PATH"] = ESTIMATOR_PATH

    try:
        proc = subprocess.run(
            [SAGE_BIN, str(WORKER_SCRIPT), params_json],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env=env,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Search timed out after {TIMEOUT_SECONDS}s.")

    if proc.returncode != 0:
        raise RuntimeError(f"Sage worker failed: {proc.stderr.strip()[:500]}")

    stdout = proc.stdout.strip()
    if not stdout:
        raise RuntimeError("Sage worker produced no output")

    last_line = stdout.splitlines()[-1]
    try:
        result = json.loads(last_line)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Could not parse worker output: {exc}\n{last_line[:300]}")

    if "error" in result:
        raise RuntimeError(result["error"])

    return result
