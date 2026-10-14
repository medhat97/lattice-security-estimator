from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


class EstimateRequest(BaseModel):
    scheme: Literal["LWE", "RLWE", "MLWE"]
    n: int = Field(..., gt=0, description="Lattice dimension (or polynomial degree for RLWE/MLWE)")
    q: int = Field(..., gt=1, description="Modulus")
    sigma: Optional[float] = Field(None, gt=0, description="Error standard deviation")
    alpha: Optional[float] = Field(None, gt=0, description="Error rate alpha = sigma/q")
    m: Optional[int] = Field(None, gt=0, description="Number of LWE samples (default: unlimited)")
    k: Optional[int] = Field(None, gt=0, description="Module rank (required for MLWE)")
    eta: Optional[int] = Field(None, gt=0, description="Centred-binomial parameter (Kyber-style)")
    secret_distribution: Literal[
        "binary", "ternary", "gaussian", "uniform", "centred_binomial"
    ] = "ternary"

    @model_validator(mode="after")
    def validate_params(self):
        needs_sigma = self.secret_distribution != "centred_binomial"
        if needs_sigma and self.sigma is None and self.alpha is None:
            raise ValueError("Provide either sigma or alpha for the error distribution")
        if self.scheme == "MLWE" and self.k is None:
            raise ValueError("k (module rank) is required for MLWE")
        if self.secret_distribution == "centred_binomial" and self.eta is None:
            raise ValueError("eta is required when secret_distribution is centred_binomial")
        return self


class AttackCost(BaseModel):
    rop_log2: Optional[float] = None
    beta: Optional[int] = None
    d: Optional[int] = None
    tag: Optional[str] = None
    error: Optional[str] = None


class EstimateResponse(BaseModel):
    lambda_bits: float
    dominant_attack: str
    attacks: dict[str, AttackCost]
    effective_n: int
    parameters_used: dict
    warnings: list[str]


class PresetItem(BaseModel):
    name: str
    scheme: str
    n: int
    q: int
    sigma: Optional[float] = None
    eta: Optional[int] = None
    k: Optional[int] = None
    secret_distribution: str
    reference: str


class KnownParams(BaseModel):
    n: Optional[int] = Field(None, gt=0)
    q: Optional[int] = Field(None, gt=1)
    sigma: Optional[float] = Field(None, gt=0)
    alpha: Optional[float] = Field(None, gt=0)
    eta: Optional[int] = Field(None, gt=0)
    k: Optional[int] = Field(None, gt=0)
    m: Optional[int] = Field(None, gt=0)
    secret_distribution: Literal[
        "binary", "ternary", "gaussian", "uniform", "centred_binomial"
    ] = "ternary"


class FindParamRequest(BaseModel):
    scheme: Literal["LWE", "RLWE", "MLWE"]
    target_lambda: float = Field(..., gt=0, description="Target bits of security")
    find_param: Literal["n", "q", "sigma", "k"]
    known: KnownParams

    @model_validator(mode="after")
    def validate_find(self):
        k = self.known
        sd = k.secret_distribution
        fp = self.find_param

        if self.scheme == "MLWE" and fp != "k" and k.k is None:
            raise ValueError("k is required in known params for MLWE when not finding k")
        if fp != "n" and k.n is None:
            raise ValueError("n is required in known params when not finding n")
        if fp != "q" and k.q is None:
            raise ValueError("q is required in known params when not finding q")
        if fp not in ("sigma", "k") and sd != "centred_binomial":
            if k.sigma is None and k.alpha is None:
                raise ValueError("sigma or alpha required when not finding sigma")
        if sd == "centred_binomial" and fp != "sigma" and k.eta is None:
            raise ValueError("eta required for centred_binomial")
        if self.scheme != "MLWE" and fp == "k":
            raise ValueError("k can only be found for MLWE")
        return self


class Verification(BaseModel):
    at_found: Optional[float] = None
    at_step_below: Optional[float] = None
    step_below_label: str


class FindParamResponse(BaseModel):
    found_param: str
    found_value: float
    verification: Verification
    parameters_complete: dict
    warnings: list[str]
