"""
Calls the Sage worker via subprocess and parses its JSON output.
All lattice-estimator logic lives in sage_worker/worker.py.
"""
import json
import os
import subprocess
from pathlib import Path

SAGE_BIN = os.environ.get(
    "SAGE_BIN",
    "/home/crc-user/miniconda3/envs/sage-env/bin/sage",
)
WORKER_SCRIPT = Path(__file__).resolve().parent.parent / "sage_worker" / "worker.py"
ESTIMATOR_PATH = os.environ.get(
    "ESTIMATOR_PATH",
    "/home/crc-user/Downloads/master-degree/my-master/implementations/Cryptanlaysis/lattice-estimator",
)
TIMEOUT_SECONDS = int(os.environ.get("ESTIMATOR_TIMEOUT", "120"))


def run_estimate(params: dict) -> dict:
    """
    Serialize params to JSON, pass to the Sage worker, return parsed result.
    Raises RuntimeError on timeout or non-zero exit.
    """
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
        raise RuntimeError(
            f"Estimation timed out after {TIMEOUT_SECONDS}s. "
            "Try smaller parameters or increase ESTIMATOR_TIMEOUT."
        )

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        raise RuntimeError(f"Sage worker failed: {stderr[:500]}")

    stdout = proc.stdout.strip()
    if not stdout:
        raise RuntimeError("Sage worker produced no output")

    # worker may print Sage startup lines before the JSON; take the last line
    last_line = stdout.splitlines()[-1]
    try:
        result = json.loads(last_line)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Could not parse worker output as JSON: {exc}\nOutput: {last_line[:300]}")

    if "error" in result:
        raise RuntimeError(result["error"])

    return result
