"""
Well-known parameter sets for auto-fill in the frontend.
sigma values for centred-binomial: sigma = sqrt(eta/2).
"""

PRESETS = [
    {
        "name": "Kyber-512",
        "scheme": "MLWE",
        "n": 256,
        "k": 2,
        "q": 3329,
        "eta": 3,
        "sigma": None,
        "secret_distribution": "centred_binomial",
        "reference": "NIST PQC Round 3 — Kyber specification",
    },
    {
        "name": "Kyber-768",
        "scheme": "MLWE",
        "n": 256,
        "k": 3,
        "q": 3329,
        "eta": 2,
        "sigma": None,
        "secret_distribution": "centred_binomial",
        "reference": "NIST PQC Round 3 — Kyber specification",
    },
    {
        "name": "Kyber-1024",
        "scheme": "MLWE",
        "n": 256,
        "k": 4,
        "q": 3329,
        "eta": 2,
        "sigma": None,
        "secret_distribution": "centred_binomial",
        "reference": "NIST PQC Round 3 — Kyber specification",
    },
    {
        "name": "Frodo-640",
        "scheme": "LWE",
        "n": 640,
        "k": None,
        "q": 32768,      # 2^15
        "eta": None,
        "sigma": 2.8,
        "secret_distribution": "gaussian",
        "reference": "FrodoKEM specification (NIST Round 3)",
    },
    {
        "name": "Frodo-976",
        "scheme": "LWE",
        "n": 976,
        "k": None,
        "q": 65536,      # 2^16
        "eta": None,
        "sigma": 2.3,
        "secret_distribution": "gaussian",
        "reference": "FrodoKEM specification (NIST Round 3)",
    },
    {
        "name": "NewHope-512",
        "scheme": "RLWE",
        "n": 512,
        "k": None,
        "q": 12289,
        "eta": 8,        # secret and error are both CBD(8), i.e. sigma = 2
        "sigma": None,
        "secret_distribution": "centred_binomial",
        "reference": "NewHope (Alkim et al. 2016)",
    },
    {
        "name": "NewHope-1024",
        "scheme": "RLWE",
        "n": 1024,
        "k": None,
        "q": 12289,
        "eta": 8,        # secret and error are both CBD(8), i.e. sigma = 2
        "sigma": None,
        "secret_distribution": "centred_binomial",
        "reference": "NewHope (Alkim et al. 2016)",
    },
]
