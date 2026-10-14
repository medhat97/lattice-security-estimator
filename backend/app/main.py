import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    EstimateRequest, EstimateResponse, AttackCost, PresetItem,
    FindParamRequest, FindParamResponse, Verification,
)
from .estimator import run_estimate
from .find_estimator import run_find
from .presets import PRESETS

ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

app = FastAPI(
    title="Lattice Security Estimator API",
    description="Estimates bit-security of LWE, RLWE, and MLWE parameter sets.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "ngrok-skip-browser-warning"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/presets", response_model=list[PresetItem])
def get_presets():
    return PRESETS


@app.post("/estimate", response_model=EstimateResponse)
def estimate(req: EstimateRequest):
    params = req.model_dump(exclude_none=True)

    try:
        result = run_estimate(params)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    attacks_typed = {
        name: AttackCost(**{k: v for k, v in cost.items() if k in AttackCost.model_fields})
        for name, cost in result.get("attacks", {}).items()
    }

    return EstimateResponse(
        lambda_bits=result["lambda_bits"],
        dominant_attack=result["dominant_attack"],
        attacks=attacks_typed,
        effective_n=result["effective_n"],
        parameters_used=params,
        warnings=result.get("warnings", []),
    )


@app.post("/find-parameter", response_model=FindParamResponse)
def find_parameter(req: FindParamRequest):
    payload = {
        "scheme": req.scheme,
        "target_lambda": req.target_lambda,
        "find_param": req.find_param,
        "known": req.known.model_dump(exclude_none=True),
    }

    try:
        result = run_find(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return FindParamResponse(
        found_param=result["found_param"],
        found_value=result["found_value"],
        verification=Verification(**result["verification"]),
        parameters_complete=result["parameters_complete"],
        warnings=result.get("warnings", []),
    )
