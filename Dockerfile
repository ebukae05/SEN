# SEN — Sensor Engine Network
# Single-stage image: installs deps, bakes preprocessed datasets, serves FastAPI.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System libs needed by torch / scipy / reportlab font rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first to maximize layer caching.
# Install CPU-only torch from PyTorch's CPU wheel index before requirements.txt
# to avoid pulling in ~2GB of NVIDIA CUDA libraries (cublas, cudnn, nccl, triton).
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install -r requirements.txt

# Copy source code, raw data, and trained model weights
COPY config.yaml preprocess.py ./
COPY agents ./agents
COPY api ./api
COPY cdh ./cdh
COPY crews ./crews
COPY models ./models
COPY tools ./tools
COPY data/raw ./data/raw

# Bake the processed datasets (FD001-FD004) and scalers into the image
RUN mkdir -p data/processed outputs/reports logs \
    && python preprocess.py --all

EXPOSE 8000

# Shell form so ${PORT} expands at runtime — Railway injects a dynamic PORT;
# locally and in docker-compose, fall back to 8000.
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
