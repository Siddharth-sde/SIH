#!/usr/bin/env bash
# run-containers.sh - Deploy the 3-container SIH26 stack using Podman Rootless
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

echo "=================================================="
echo "  Deploying 3-Container SIH26 Architecture"
echo "  1. ollama (LLM Engine - Port 11434)"
echo "  2. ml-service (ML Engine - Port 8001)"
echo "  3. app (Backend + Frontend Host - Ports 8000 & 5173)"
echo "=================================================="

# Detect compose tool
if podman compose version >/dev/null 2>&1; then
    COMPOSE_CMD="podman compose"
elif command -v podman-compose >/dev/null 2>&1; then
    COMPOSE_CMD="podman-compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    echo "[-] No container compose tool found."
    echo "    On Fedora, run: sudo dnf install -y podman-compose"
    exit 1
fi

# Check if Ollama is already running on port 11434
if curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "[*] Existing Ollama service detected on :11434. Starting ml-service and app containers..."
    ${COMPOSE_CMD} up -d --build ml-service app
else
    echo "[*] Starting all 3 containers via ${COMPOSE_CMD}..."
    ${COMPOSE_CMD} up -d --build
fi

echo ""
echo "=================================================="
echo "  Containers deployed successfully:"
echo "  - Frontend UI:       http://localhost:5173"
echo "  - Backend API:       http://localhost:8000"
echo "  - ML Engine:         http://localhost:8001"
echo "  - Ollama Engine:     http://localhost:11434"
echo ""
echo "  View logs:   ${COMPOSE_CMD} logs -f"
echo "  Stop stack:  ${COMPOSE_CMD} down"
echo "=================================================="
