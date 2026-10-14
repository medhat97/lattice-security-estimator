FROM sagemath/sagemath:latest

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Web-layer deps go into the SYSTEM python3 (uvicorn/fastapi/pydantic/dotenv).
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# lattice-estimator is imported at runtime by the Sage worker (Sage python has scipy/numpy).
RUN git clone https://github.com/malb/lattice-estimator.git /opt/lattice-estimator && git -C /opt/lattice-estimator checkout 3e48ef4

COPY app/ ./app/
COPY sage_worker/ ./sage_worker/

ENV SAGE_BIN=/usr/bin/sage \
    ESTIMATOR_PATH=/opt/lattice-estimator \
    ESTIMATOR_TIMEOUT=120

EXPOSE 8000

# The base image entrypoint funnels commands through "sage -sh"; override it so
# uvicorn runs on system python3. The worker calls $SAGE_BIN itself for Sage env.
ENTRYPOINT []
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
