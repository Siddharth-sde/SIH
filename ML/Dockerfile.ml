# National Material Master - ML Engine Container
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for openBLAS
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Pre-download and save SentenceTransformer model weights for complete offline support
RUN mkdir -p /app/models && \
    python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('all-MiniLM-L6-v2'); model.save('/app/models/all-MiniLM-L6-v2')"

# Copy source code, test suite, and pre-processed golden outputs
COPY src/ /app/src/
COPY data/ /app/data/
COPY tests/ /app/tests/
COPY material_master_input.csv ground_truth_clusters.csv /app/

ENV PYTHONPATH=/app
ENV HF_HUB_OFFLINE=1
ENV EMBEDDING_MODEL_PATH=/app/models/all-MiniLM-L6-v2

EXPOSE 8001

CMD ["uvicorn", "src.ml_service:app", "--host", "0.0.0.0", "--port", "8001"]
