#!/usr/bin/env bash
# run-local.sh - Launch the full SIH26 stack locally (native processes)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
NODE_BIN="${ROOT_DIR}/Frontend/node_modules/.bin"

export PATH="${VENV_DIR}/bin:${NODE_BIN}:${PATH}"
export PYTHONPATH="${ROOT_DIR}/ML:${ROOT_DIR}"

echo "=================================================="
echo "  Starting National Material Master Platform"
echo "=================================================="

# Ensure Python venv exists
if [ ! -f "${VENV_DIR}/bin/uvicorn" ]; then
    echo "[-] Virtual environment missing or incomplete at ${VENV_DIR}."
    echo "    Please create it with: python3 -m venv .venv && .venv/bin/pip install -r ML/requirements.txt -r Backend/requirements.txt"
    exit 1
fi

# Cleanup on exit
cleanup() {
    echo ""
    echo "[*] Shutting down services..."
    kill -TERM "${PID_ML:-}" 2>/dev/null || true
    kill -TERM "${PID_BACKEND:-}" 2>/dev/null || true
    kill -TERM "${PID_FRONTEND:-}" 2>/dev/null || true
    wait 2>/dev/null || true
    echo "[+] All services stopped."
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start ML Service (:8001)
echo "[1/3] Starting ML Microservice on :8001..."
ML_PORT=8001 uvicorn ML.src.ml_service:app --host 0.0.0.0 --port 8001 > "${ROOT_DIR}/ml_service.log" 2>&1 &
PID_ML=$!

# 2. Start Backend Gateway (:8000)
echo "[2/3] Starting Backend API Gateway on :8000..."
uvicorn Backend.main:app --host 0.0.0.0 --port 8000 > "${ROOT_DIR}/backend.log" 2>&1 &
PID_BACKEND=$!

# 3. Start Frontend Dev Server (:5173)
echo "[3/3] Starting Frontend (Vite) on :5173..."
(cd "${ROOT_DIR}/Frontend" && npm run dev -- --host 0.0.0.0 --port 5173) > "${ROOT_DIR}/frontend.log" 2>&1 &
PID_FRONTEND=$!

# Wait for startup
sleep 3
echo "=================================================="
echo "  Platform is ONLINE:"
echo "  - Frontend UI:       http://localhost:5173"
echo "  - Backend Gateway:   http://localhost:8000/docs"
echo "  - ML Engine API:     http://localhost:8001/docs"
echo "  Press Ctrl+C to terminate all services."
echo "=================================================="

wait
