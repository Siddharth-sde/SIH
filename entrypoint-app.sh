#!/usr/bin/env bash
set -e

echo "=================================================="
echo "  Starting Unified App Host (Backend + Frontend)"
echo "=================================================="

# Start Uvicorn Backend Gateway in background
echo "[*] Launching Backend Gateway (Uvicorn) on 0.0.0.0:8000..."
uvicorn main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

# Start Nginx in foreground
echo "[*] Launching Frontend Web Server (Nginx) on 0.0.0.0:5173..."
nginx -g "daemon off;" &
NGINX_PID=$!

cleanup() {
    echo ""
    echo "[*] Stopping Backend and Nginx..."
    kill -TERM "$UVICORN_PID" "$NGINX_PID" 2>/dev/null || true
    wait "$UVICORN_PID" "$NGINX_PID" 2>/dev/null || true
    echo "[+] Unified app stopped."
}
trap cleanup SIGINT SIGTERM EXIT

# Wait for any process to exit
wait -n "$UVICORN_PID" "$NGINX_PID"
