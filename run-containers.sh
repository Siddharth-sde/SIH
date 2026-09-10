#!/usr/bin/env bash
# run-containers.sh - Orchestrate SIH26 rootless containers using Podman
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

echo "=================================================="
echo "  Deploying SIH26 Stack via Podman Rootless"
echo "=================================================="

# Check if podman compose or podman-compose is available
if podman compose version >/dev/null 2>&1; then
    COMPOSE_CMD="podman compose"
elif command -v podman-compose >/dev/null 2>&1; then
    COMPOSE_CMD="podman-compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    echo "[-] No container compose tool found (podman compose, podman-compose, or docker-compose)."
    echo "    On Fedora, run: sudo dnf install -y podman-compose"
    exit 1
fi

echo "[*] Using compose engine: ${COMPOSE_CMD}"
${COMPOSE_CMD} up -d --build

echo ""
echo "=================================================="
echo "  Containers deployed successfully:"
echo "  - Frontend:          http://localhost:5173"
echo "  - Backend Gateway:   http://localhost:8000"
echo "  - ML Engine:         http://localhost:8001"
echo ""
echo "  To view logs:    ${COMPOSE_CMD} logs -f"
echo "  To stop:         ${COMPOSE_CMD} down"
echo "=================================================="
