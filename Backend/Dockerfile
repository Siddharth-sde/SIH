# Use an official lightweight Python runtime for Linux
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set standard working directory inside the container
WORKDIR /app

# Install system-level build tools and utilities needed on Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list first to leverage Docker layer caching
COPY requirements.txt .

# Upgrade pip and install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire backend application code into the container
COPY . .

# Expose FastAPI's standard port
EXPOSE 8000

# Start Uvicorn bound to 0.0.0.0 so external machines/browsers can reach it
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]