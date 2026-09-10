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
RUN pip install --no-cache-dir -r requirements.txt

# Copy offline model weights
COPY models/ /app/models/

# Copy source code and pre-processed golden outputs
COPY src/ /app/src/
COPY data/ /app/data/

ENV PYTHONPATH=/app
ENV HF_HUB_OFFLINE=1

EXPOSE 8001

CMD ["uvicorn", "src.ml_service:app", "--host", "0.0.0.0", "--port", "8001"]
